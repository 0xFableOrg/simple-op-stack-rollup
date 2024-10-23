"""
This module abstracts the use of ansible for managing cloud deployments.
"""

import json
import yaml

import libroll as lib
from config import Config


def generate_inventory(config: Config):
    unique_hosts = set(
        [
            config.l1_node_remote_ip,
            config.l2_engine_remote_ip,
            config.l2_sequencer_remote_ip,
            config.l2_proposer_remote_ip,
            config.l2_batcher_remote_ip,
        ]
    )

    inventory = {
        "l1": {"hosts": {"l1": {"ansible_host": config.l1_node_remote_ip}}},
        "l2_engine": {
            "hosts": {"l2-engine": {"ansible_host": config.l2_engine_remote_ip}}
        },
        "l2_sequencer": {
            "hosts": {"l2-sequencer": {"ansible_host": config.l2_sequencer_remote_ip}}
        },
        "l2_proposer": {
            "hosts": {"l2-proposer": {"ansible_host": config.l2_proposer_remote_ip}}
        },
        "l2_batcher": {
            "hosts": {"l2-batcher": {"ansible_host": config.l2_batcher_remote_ip}}
        },
        "l2": {
            "hosts": {
                "l2-engine": {},
                "l2-sequencer": {},
                "l2-proposer": {},
                "l2-batcher": {},
            }
        },
        "unique_hosts": {"hosts": {}},
    }

    for host in unique_hosts:
        inventory["unique_hosts"]["hosts"][host] = {"ansible_host": host}

    # Write the inventory dictionary to a YAML file
    ansible_dir = config.paths.ansible_dir
    with open(f"{ansible_dir}/inventory.yml", "w") as file:
        yaml.dump(inventory, file, default_flow_style=False)


def run_playbook(config: Config, descr, log_file, playbook, extra_vars=None, tags=None):
    ansible_dir = config.paths.ansible_dir
    command = f"ansible-playbook -i inventory.yml playbooks/{playbook}"

    if extra_vars is not None:
        command = f"{command} --extra-vars='{json.dumps(extra_vars, separators=(',', ':'))}'"

    if config.ansible_ssh_user is not None:
        command = f"{command} --user {config.ansible_ssh_user}"

    if config.ansible_ssh_key is not None:
        command = f"{command} --key-file {config.ansible_ssh_key}"

    if tags is not None:
        command = f"{command} --tags {','.join(tags)}"

    print(f"Running ansible {playbook}. Logging to {log_file}")
    lib.run(descr, command, cwd=ansible_dir, forward="fd", stdout=log_file)
