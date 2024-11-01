import os

import l2
from config import Config
import libroll as lib
from processes import PROCESS_MGR


####################################################################################################

def start(config: Config, sequencer: bool = True):
    """
    Starts the OP node, which derives the L2 chain from the L1 chain & optionally creates new L2
    blocks, then waits for it to be reasy.
    """

    lib.ensure_port_unoccupied(
        "L2 node", config.l2_node_rpc_listen_addr, config.l2_node_rpc_listen_port)

    l2.generate_jwt_secret(config)

    log_file = config.l2_node_log_file
    print(f"Starting L2 node. Logging to {log_file}")

    command = [
        "op-node",

        # Node-Specific Options
        # https://github.com/ethereum-optimism/optimism/blob/develop/op-node/flags/flags.go
        f"--l1={config.l1_rpc_for_node_url}",
        f"--l2={config.l2_engine_authrpc_url}",
        f"--l2.jwt-secret={os.path.join(config.jwt_secret_path)}",
        f"--verifier.l1-confs={config.l2_node_verifier_l1_confs}",
        f"--rollup.config={os.path.join('..', config.rollup_config_path)}",
        f"--l1.rpckind={config.l2_node_l1_rpc_kind}",

        # Sequencer Options

        *([] if not sequencer else [
            "--sequencer.enabled",
            f"--sequencer.l1-confs={config.l2_node_sequencer_l1_confs}",
        ]),

        # RPC Options
        # https://github.com/ethereum-optimism/optimism/blob/develop/op-service/rpc/cli.go

        f"--rpc.addr={config.l2_node_rpc_listen_addr}",
        f"--rpc.port={config.l2_node_rpc_listen_port}",

        # P2P Flags
        # https://github.com/ethereum-optimism/optimism/blob/develop/op-node/flags/p2p_flags.go

        *(["--p2p.disable"] if not config.l2_node_p2p_enabled else [
            f"--p2p.static={config.l2_node_p2p_static_peers}",
            f"--p2p.listen.ip={config.l2_node_p2p_listen_addr}",
            f"--p2p.listen.tcp={config.l2_node_p2p_tcp_listen_port}",
            f"--p2p.listen.udp={config.l2_node_p2p_udp_listen_port}",
            f"--p2p.priv.path={config.p2p_peer_key_path}",
            *([] if config.p2p_sequencer_key is None else [
                f"--p2p.sequencer.key={config.p2p_sequencer_key}"
            ])
        ]),

        # Metrics Options
        # https://github.com/ethereum-optimism/optimism/blob/develop/op-service/metrics/cli.go

        *([] if not config.l2_node_metrics else [
            "--metrics.enabled",
            f"--metrics.port={config.l2_node_metrics_listen_port}",
            f"--metrics.addr={config.l2_node_metrics_listen_addr}"])
    ]

    config.log_l2_command("\n".join(command))

    def on_exit():
        print(f"L2 node exited. Check {log_file} for details.\n"
              "You can re-run with `./rollop l2-node` in another terminal\n"
              "(!! Make sure to specify the same config file and flags!)")

    PROCESS_MGR.start(
        "starting L2 node",
        command,
        # so that `opnode_*_db` directories get created under the db directory
        cwd=config.databases_dir,
        file=log_file,
        on_exit=on_exit)

    lib.wait_for_rpc_server("127.0.0.1", config.l2_node_rpc_listen_port)


####################################################################################################

def clean(config: Config):
    """
    Delete the L2 node's p2p databases.
    """
    lib.remove_paths(config, [
        "opnode_discovery_db",
        "opnode_peerstore_db",
    ])


####################################################################################################
