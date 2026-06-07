// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title  VingelSimGate
 * @notice On-chain gating and result anchoring for VINGEL Market Simulator.
 *
 * Workflow
 * ────────
 * 1. User provides their Monad wallet address in the VINGEL UI.
 * 2. Backend calls requestSimulation(user, productHash):
 *      • Checks user holds ≥ MIN_BALANCE MON.
 *      • Assigns a unique jobId (keccak256 of args + timestamp).
 *      • Emits SimulationRequested(jobId, user, productHash).
 * 3. Backend runs the Sarvam AI + NumPy simulation (off-chain).
 * 4. Backend calls storeResult(jobId, resultHash):
 *      • Only the contract owner (backend wallet) can call this.
 *      • Anchors a SHA-256 hash of the result JSON on-chain.
 *      • Emits SimulationCompleted(jobId, resultHash).
 * 5. Anyone can call verifyResult(jobId, resultHash) to confirm authenticity.
 *
 * Monad Testnet
 * ─────────────
 *   RPC:      https://testnet-rpc.monad.xyz
 *   Chain ID: 10143
 *   Symbol:   MON
 *   Explorer: https://testnet.monadexplorer.com
 *   Faucet:   https://faucet.monad.xyz
 *
 * Deploy
 * ──────
 *   python blockchain/deploy_simgate.py
 */
contract VingelSimGate {

    // ── Config ────────────────────────────────────────────────────────────────

    /// Minimum MON balance (in wei) a user must hold to request a simulation.
    /// Default: 0.01 MON — easy to obtain from the faucet.
    uint256 public constant MIN_BALANCE = 0.01 ether;

    /// The deployer wallet — only this address can call storeResult().
    address public immutable owner;

    // ── Data ──────────────────────────────────────────────────────────────────

    enum JobStatus { Pending, Completed }

    struct SimJob {
        bytes32    jobId;
        address    user;           // user's wallet address (balance-checked)
        bytes32    productHash;    // keccak256 of product JSON (fingerprint)
        bytes32    resultHash;     // keccak256 of result JSON (set after completion)
        uint256    requestedAt;    // block.timestamp when job was created
        uint256    completedAt;    // block.timestamp when result was stored (0 if pending)
        JobStatus  status;
    }

    mapping(bytes32 => SimJob)   private _jobs;
    mapping(address => bytes32[]) private _userJobs;
    uint256 private _jobCounter;

    // ── Events ────────────────────────────────────────────────────────────────

    event SimulationRequested(
        bytes32 indexed jobId,
        address indexed user,
        bytes32         productHash,
        uint256         requestedAt
    );

    event SimulationCompleted(
        bytes32 indexed jobId,
        bytes32         resultHash,
        uint256         completedAt
    );

    // ── Errors ────────────────────────────────────────────────────────────────

    error InsufficientBalance(address user, uint256 balance, uint256 required);
    error JobNotFound(bytes32 jobId);
    error JobAlreadyCompleted(bytes32 jobId);
    error NotOwner();
    error ZeroAddress();
    error ZeroHash();

    // ── Constructor ───────────────────────────────────────────────────────────

    constructor() {
        owner = msg.sender;
    }

    // ── Modifiers ─────────────────────────────────────────────────────────────

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    // ── Write: called by backend wallet ──────────────────────────────────────

    /**
     * @notice Gate a simulation request by checking the user's MON balance.
     * @param  user         The user's Monad wallet address to balance-check.
     * @param  productHash  keccak256 fingerprint of the product JSON.
     * @return jobId        Unique identifier for this simulation job.
     *
     * Reverts with InsufficientBalance if user holds < MIN_BALANCE MON.
     * Only the owner (backend wallet) can call this.
     */
    function requestSimulation(address user, bytes32 productHash)
        external
        onlyOwner
        returns (bytes32 jobId)
    {
        if (user == address(0))  revert ZeroAddress();
        if (productHash == bytes32(0)) revert ZeroHash();

        // ── Balance gate ──────────────────────────────────────────────────────
        uint256 bal = user.balance;
        if (bal < MIN_BALANCE) {
            revert InsufficientBalance(user, bal, MIN_BALANCE);
        }

        // ── Assign job ID ─────────────────────────────────────────────────────
        _jobCounter++;
        jobId = keccak256(abi.encodePacked(user, productHash, block.timestamp, _jobCounter));

        _jobs[jobId] = SimJob({
            jobId:       jobId,
            user:        user,
            productHash: productHash,
            resultHash:  bytes32(0),
            requestedAt: block.timestamp,
            completedAt: 0,
            status:      JobStatus.Pending
        });
        _userJobs[user].push(jobId);

        emit SimulationRequested(jobId, user, productHash, block.timestamp);
    }

    /**
     * @notice Anchor the simulation result hash on-chain.
     * @param  jobId       The job ID returned by requestSimulation().
     * @param  resultHash  keccak256 / SHA-256 hash of the result JSON.
     *
     * Only the contract owner (backend wallet) can call this.
     * Reverts if the job is not found or already completed.
     */
    function storeResult(bytes32 jobId, bytes32 resultHash)
        external
        onlyOwner
    {
        if (resultHash == bytes32(0)) revert ZeroHash();

        SimJob storage job = _jobs[jobId];
        if (job.requestedAt == 0) revert JobNotFound(jobId);
        if (job.status == JobStatus.Completed) revert JobAlreadyCompleted(jobId);

        job.resultHash  = resultHash;
        job.completedAt = block.timestamp;
        job.status      = JobStatus.Completed;

        emit SimulationCompleted(jobId, resultHash, block.timestamp);
    }

    // ── Read (view — no gas for callers) ─────────────────────────────────────

    /**
     * @notice Retrieve full job details by jobId.
     */
    function getJob(bytes32 jobId)
        external
        view
        returns (
            address user,
            bytes32 productHash,
            bytes32 resultHash,
            uint256 requestedAt,
            uint256 completedAt,
            bool    completed
        )
    {
        SimJob storage job = _jobs[jobId];
        if (job.requestedAt == 0) revert JobNotFound(jobId);
        return (
            job.user,
            job.productHash,
            job.resultHash,
            job.requestedAt,
            job.completedAt,
            job.status == JobStatus.Completed
        );
    }

    /**
     * @notice Verify that a given resultHash matches the on-chain record.
     * @return matches  true if resultHash equals the stored hash.
     * @return storedAt Unix timestamp when the result was anchored.
     */
    function verifyResult(bytes32 jobId, bytes32 resultHash)
        external
        view
        returns (bool matches, uint256 storedAt)
    {
        SimJob storage job = _jobs[jobId];
        if (job.requestedAt == 0) return (false, 0);
        return (
            job.status == JobStatus.Completed && job.resultHash == resultHash,
            job.completedAt
        );
    }

    /**
     * @notice Return all job IDs for a given user wallet.
     */
    function getUserJobs(address user)
        external
        view
        returns (bytes32[] memory)
    {
        return _userJobs[user];
    }

    /**
     * @notice Return the current minimum MON balance required (in MON, not wei).
     */
    function minBalanceMON() external pure returns (uint256) {
        return MIN_BALANCE / 1 ether;
    }
}
