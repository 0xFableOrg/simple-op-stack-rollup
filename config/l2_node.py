class L2NodeConfig:
    """
    Configuration options related to the L2 node.
    """

    # ==============================================================================================

    def __init__(self):
        super().__init__()

        self.l2_node_sequencer_l1_confs = 0
        """
        Minimum number of L1 blocks that the L1 origin of L2 block must be behind the L1 head (0 by
        default).
        """

        self.l2_node_verifier_l1_confs = 0
        """
        Don't attempt to derive L2 blocks from L1 blocks that are less than this number of L1 blocks
        before the L1 head. (While L1 reorgs are supported, they are slow to perform.)
        """

        self.l2_node_l1_rpc_kind = "basic"
        """
        The kind of RPC provider for L1 access, used to inform optimal transactions receipts
        fetching, and thus reduce costs. Valid options: alchemy, quicknode, infura, parity,
        nethermind, debug_geth, erigon, basic, any. Default: basic.
        
        "Basic" only tries basic methods, while "any" tries any available method.
        """

        # === RPC ===

        self.l2_node_enable_admin = False
        """
        Whether the "admin" namespace node API is enabled (False by default). This API allows
        starting, stopping, and querying the status of the sequencer (cf.
        https://github.com/ethereum-optimism/optimism/blob/develop/op-node/sources/rollupclient.go).
        """

        self.l2_node_rpc_listen_addr = "0.0.0.0"
        """
        Address the node RPC server should bind to ("0.0.0.0" by default).
        
        Used for the "optimism" namespace API
        (https://community.optimism.io/docs/developers/build/json-rpc/) and the "admin" namespace
        (cf. :py:attr:`node_enable_admin`).
        """

        self.l2_node_rpc_listen_port = 7545
        """
        Port the node RPC server should bind to (7545 by default).
        
        Used for the "optimism" namespace API
        (https://community.optimism.io/docs/developers/build/json-rpc/) and the "admin" namespace
        (cf. :py:attr:`node_enable_admin`).
        """

        # === P2P Options ===

        self.l2_node_p2p_static_peers = ""
        """
        Comma-separated list of bootnodes to connect to.
        """

        self.l2_node_p2p_enabled = False
        """
        Whether to enable P2P (peer discovery + block gossip — False by default).
        """

        self.l2_node_p2p_listen_addr = "0.0.0.0"
        """
        IP to bind LibP2P and Discv5 to.
        """

        self.l2_node_p2p_tcp_listen_port = 9222
        """
        TCP port to bind LibP2P to. Any available system port if set to 0.
        """

        self.l2_node_p2p_udp_listen_port = 0
        """
        UDP port to bind Discv5 to. Same as TCP port if left 0.
        """

        # === Metrics ===

        self.l2_node_metrics = False
        """
        Whether to record metrics in the L2 node (False by default).
        """

        self.l2_node_metrics_listen_port = 7300
        """
        Port to the l2 node metrics server should bind to (7300 by default).
        Ignored if :py:attr:`l2_node_metrics` is False.
        """

        self.l2_node_metrics_listen_addr = "0.0.0.0"
        """
        Address the L2 node metrics server should bind to ("0.0.0.0" by default).
        Ignored if :py:attr:`l2_node_metrics` is False.
        """

    # ==============================================================================================

    # Other options needed to configure the L2 node:
    # :py:attr:`jwt_secret_path` in :py:class:`config.PathConfig`
    # :py:attr:`rollup_config_path` in :py:class:`config.PathConfig`
    # :py:attr:`p2p_peer_key_path` in :py:class:`config.PathConfig`
    # :py:attr:`p2p_sequencer_key` in :py:class:`config.AccountsKeysConfig`
    # :py:attr:`l1_rpc_for_node_url` in :py:class:`config.NetworkConfig`
    # :py:attr:`l2_engine_authrpc_url` in :py:class:`config.NetworkConfig`

    # See also:
    # :py:attr:`l2_chain_id` in :py:class:`config.NetworkConfig`
    #   (This is not configured on the node, but on the engine!)

    # ==============================================================================================
