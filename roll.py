#!/usr/bin/env python3

"""
This is the entry point for roll-op system, responsible for parsing command line arguments and
invoking the appropriate commands.
"""

import os
import shutil

import block_explorer
import account_abstraction
import deps
import l1
import l2
import l2_batcher
import l2_deploy
import l2_engine
import l2_node
import l2_proposer
import libroll as lib
import logrotate
from argparsing import Argparser
from config import Config, use_production_config
from processes import PROCESS_MGR
import setup
import state

####################################################################################################

p = Argparser(
    program_name="rollop",
    description="R|Helps you spin up an op-stack rollup.\n"
                "Use `rollop <command> --help` to get more detailed help for a command.",
)

# --------------------------------------------------------------------------------------------------
# Global Options

p.arg(
    "--name",
    help="name of the rollup deployment",
    default=None,
    dest="name")

p.arg(
    "--preset",
    help="use a preset rollup configuration",
    choices=["dev", "prod"],
    default=None,
    dest="preset")

p.arg(
    "--config",
    help="path to the config file",
    default=None,
    dest="config_path")

p.arg(
    "--clean",
    help="clean command-related output before running the specified command",
    default=False,
    dest="clean_first",
    action="store_true")

p.arg(
    "--no-ansi-esc",
    help="disable ANSI escape codes for terminal manipulation",
    default=True,
    dest="use_ansi_esc",
    action="store_false")

p.arg(
    "--yes",
    default=False,
    dest="always_yes",
    action="store_true",
    help="answer yes to all prompts (install all requested dependencies)")

# --------------------------------------------------------------------------------------------------
p.delimiter("MAIN COMMANDS")

p.command(
    "help",
    help="show this help message and exit")

p.command(
    "setup",
    help="installs prerequisites and builds the optimism repository")

cmd_devnet = p.command(
    "devnet",
    help="starts a local devnet, comprising an L1 node and all L2 components")

p.command(
    "clean",
    help="cleans up deployment outputs and databases")

cmd_l2 = p.command(
    "l2",
    help="starts an L2 blockchain, deploying the contracts if needed")

p.command(
    "aa",
    help="starts an ERC-4337 bundler and a paymaster signer service")

p.command(
    "explorer",
    help="starts a block explorer")

# --------------------------------------------------------------------------------------------------
p.delimiter("GRANULAR COMMANDS")

p.command(
    "l1",
    help="starts a local L1 node",
    description="Starts a local L1 node, initializing it if needed.")

p.command(
    "deploy-l2",
    help="deploys but does not start an L2 chain",
    description="Deploys but does not start an L2 chain: "
                "creates the genesis and deploys the contracts to L1.")

p.command(
    "l2-engine",
    help="starts a local L2 execution engine (op-geth) node",
    description="Starts a local L2 execution engine (op-geth) node, initializing it if needed.")

p.command(
    "l2-sequencer",
    help="starts a local L2 node (op-node) in sequencer mode")

p.command(
    "l2-node",
    help="starts a local L2 node (op-node) in non-sequencer mode")

p.command(
    "l2-batcher",
    help="starts a local L2 transaction batcher")

p.command(
    "l2-proposer",
    help="starts a local L2 output roots proposer")

# --------------------------------------------------------------------------------------------------
p.delimiter("CLEANUP")

p.command(
    "clean-build",
    help="cleans up build outputs (but not deployment outputs)",
    description="Cleans up build outputs — leaves deployment outputs intact, "
                "as well as anything that was downloaded. "
                "Mostly used to get the the downloaded repos to rebuild. "
                "Requires rerunning make setup after running!")

p.command(
    "clean-l2",
    help="cleans up L2 deployment outputs")

p.command(
    "clean-aa",
    help="cleans up deployment outputs for account abstraction",
)

p.command(
    "clean-explorer",
    help="deletes the block explorer databases, logs, and containers")

# --------------------------------------------------------------------------------------------------
# Command-Specific Options

for cmd in [cmd_l2, cmd_devnet]:
    cmd.arg(
        "--explorer",
        help="deploys a blockscout explorer for the L2 chain (NOT FUNCTIONAL)",
        default=False,
        dest="explorer",
        action="store_true")

    cmd.arg(
        "--aa",
        help="starts an ERC4337 bundler and a paymaster signer service",
        default=False,
        dest="aa",
        action="store_true")


####################################################################################################

def load_config() -> Config:
    """
    Uses the program arguments (found at `state.args`) to create and populate a :py:class:`Config`
    object.
    """

    deployment_name = state.args.name
    deployment_name = deployment_name if deployment_name else "rollup"

    config = Config(deployment_name)

    # Define config preset
    if state.args.preset is None or state.args.preset == "dev":
        pass
    elif state.args.preset == "prod":
        use_production_config(config)
    else:
        # Should never happen, as correct preset is validated by argparse.
        raise Exception(f"Unknown preset: '{state.args.preset}'. Valid: 'dev', 'prod'.")

    config.deployment_name = deployment_name

    # Parse config file if specified
    if state.args.config_path:
        try:
            import tomli
        except Exception:
            raise Exception(
                "Missing dependencies. Try running `rollop setup` first.")
        if os.path.exists(state.args.config_path):
            with open(state.args.config_path, mode="rb") as f:
                config_file = tomli.load(f)
        else:
            raise Exception(f"Cannot find config file at {state.args.config_path}")

        try:
            for key, value in config_file.items():
                if hasattr(config, key):
                    setattr(config, key, value)

            if config_file.get("batch_inbox_address") is None:
                # Derive a unique batch inbox address from the chain id.
                addr = "0xff69000000000000000000000000000000000000"
                str_id = str(config.l2_chain_id)
                config.batching_inbox_address = addr[:-len(str_id)] + str_id

            recommended_options = [
                "l1_chain_id",
                "l2_chain_id",
                "l1_rpc_url",
                "contract_deployer_key",
                "batcher_account",
                "batcher_key",
                "proposer_account",
                "proposer_key",
                "admin_account",
                "admin_key",
                "p2p_sequencer_account",
                "p2p_sequencer_key",
            ]
            for option in recommended_options:
                if config_file.get(option) is None:
                    print(f"Warning: config file does not specify `{option}`.\n"
                          "It is highly recommended to specify this option, "
                          "especially for non-local deployments.")

            if config_file.get("l1_rpc_url") is not None \
                    and config_file.get("l1_rpc_for_node_url") is None:
                print("Config file specifies l1_rpc_url but not l1_rpc_for_node_url.\n"
                      "Automatically setting l1_rpc_for_node_url to the same value.")
                config.l1_rpc_for_node_url = config.l1_rpc_url

        except KeyError as e:
            raise Exception(f"Missing config file value: {e}")

    config.validate()

    return config


####################################################################################################

def start_addons(config: Config):
    """
    Starts a block explorer and/or an ERC4337 bundler and paymaster, if configured to do so.
    """
    if getattr(state.args, "explorer", None):
        block_explorer.launch_blockscout(config)
    if getattr(state.args, "aa", None):
        account_abstraction.setup(config)
        account_abstraction.deploy(config)
        account_abstraction.start(config)


####################################################################################################

def wait(config: Config):
    """
    Prevents the main process from shutdowning while subprocesses are running, and also
    starts the logrotate thread.
    """
    logrotate.start_thread(config)
    PROCESS_MGR.wait_all()


####################################################################################################

def main():
    state.args = p.parse()
    config = None

    try:
        if state.args.command is None or state.args.command == "help":
            p.print_help()
            exit()

        deps.basic_setup()
        config = load_config()
        deps.create_paths(config)

        if state.args.command == "setup":
            setup.setup(config)
            return

        deps.post_setup()

        if state.args.command == "devnet":
            if state.args.clean_first:
                l1.clean(config)
                l2.clean(config)

            deps.check_or_install_geth()
            deps.check_or_install_foundry()

            if config.run_devnet_l1:
                l1.deploy_devnet_l1(config)
            l2.deploy_and_start(config)
            start_addons(config)
            wait(config)

        elif state.args.command == "clean":
            if getattr(state.args, "aa", None):
                account_abstraction.clean(config)
            if getattr(state.args, "explorer", None):
                block_explorer.clean(config)
            l1.clean(config)
            l2.clean(config)
            shutil.rmtree(config.deployment_dir, ignore_errors=True)

        elif state.args.command == "l2":
            if state.args.clean_first:
                l2.clean(config)

            deps.check_or_install_foundry()

            l2.deploy_and_start(config)
            start_addons(config)
            wait(config)

        elif state.args.command == "aa":
            if state.args.clean_first:
                account_abstraction.clean(config)

            account_abstraction.setup(config)
            account_abstraction.deploy(config)
            account_abstraction.start(config)
            wait(config)

        elif state.args.command == "explorer":
            if state.args.clean_first:
                block_explorer.clean(config)

            block_explorer.launch_blockscout(config)
            wait(config)

        elif state.args.command == "l1":
            if state.args.clean_first:
                l1.clean(config)

            deps.check_or_install_geth()
            deps.check_or_install_foundry()

            l1.deploy_devnet_l1(config)
            wait(config)

        elif state.args.command == "deploy-l2":
            if state.args.clean_first:
                l2.clean(config)

            deps.check_or_install_foundry()

            l2_deploy.deploy(config)

        elif state.args.command == "l2-engine":
            if state.args.clean_first:
                l2_engine.clean(config)

            l2_engine.start(config)
            if hasattr(state.args, "explorer") and state.args.explorer:
                block_explorer.launch_blockscout(config)
            wait(config)

        elif state.args.command == "l2-sequencer":
            if state.args.clean_first:
                l2_node.clean(config)

            l2_node.start(config, sequencer=True)
            wait(config)

        elif state.args.command == "l2-node":
            if state.args.clean_first:
                l2_node.clean(config)

            l2_node.start(config, sequencer=False)
            wait(config)

        elif state.args.command == "l2-batcher":
            # nothing to clean
            l2_batcher.start(config)
            wait(config)

        elif state.args.command == "l2-proposer":
            # nothing to clean
            config.deployments = lib.read_json_file(config.addresses_path)
            l2_proposer.start(config)
            wait(config)

        elif state.args.command == "clean-build":
            setup.clean_build()

        elif state.args.command == "clean-l2":
            l2.clean(config)

        elif state.args.command == "clean-aa":
            account_abstraction.clean(config)

        elif state.args.command == "clean-explorer":
            block_explorer.clean(config)

        print("Done.")
    except KeyboardInterrupt:
        # Usually not triggered because we will exit via the exit hook handler.
        print("Interrupted by user.")
    except Exception as e:
        if config is None:
            raise e
        else:
            import traceback
            trace_path = os.path.join(config.logs_dir, "trace.log")
            with open(trace_path, "w") as f:
                f.write(str(e))
                f.write(traceback.format_exc())
            print(f"Aborted with error: {e}\n"
                  f"See log file for full trace: {trace_path}")
            exit(1)


####################################################################################################

if __name__ == "__main__":
    main()

####################################################################################################
