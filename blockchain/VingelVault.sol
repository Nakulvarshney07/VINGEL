// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title  VingelVault
 * @notice Anchors encrypted product simulation hashes on Monad.
 *
 * How it works
 * ────────────
 * 1. VINGEL encrypts product data locally (HMAC-SHA256 / Fernet) and stores
 *    it in the local ledger (blockchain/vault.py).
 * 2. The local block's SHA-256 hash (bytes32) is then anchored here on Monad.
 *    No encrypted data ever leaves the user's machine.
 * 3. Anyone can call verifyBlock() to confirm a given hash was anchored by a
 *    specific wallet — proving the data existed at that block timestamp.
 *
 * Deploy to Monad Testnet
 * ───────────────────────
 *   python blockchain/deploy_monad.py
 *
 * Monad Testnet
 *   RPC:      https://testnet-rpc.monad.xyz
 *   Chain ID: 10143
 *   Symbol:   MON
 *   Explorer: https://testnet.monadexplorer.com
 *   Faucet:   https://faucet.monad.xyz
 */
contract VingelVault {

    // ── Data ─────────────────────────────────────────────────────────────────

    struct BlockRecord {
        bytes32 blockHash;
        uint256 storedAt;   // block.timestamp when anchored
        address owner;      // msg.sender who anchored it
    }

    mapping(bytes32 => BlockRecord) private _records;
    mapping(address => bytes32[])   private _ownerBlocks;

    // ── Events ────────────────────────────────────────────────────────────────

    event BlockStored(
        address indexed owner,
        bytes32 indexed blockHash,
        uint256         storedAt
    );

    // ── Errors ────────────────────────────────────────────────────────────────

    error AlreadyStored(bytes32 blockHash);
    error ZeroHash();

    // ── Write ─────────────────────────────────────────────────────────────────

    /**
     * @notice Anchor a VINGEL local-chain block hash on Monad.
     * @param  blockHash  The SHA-256 hex hash from vault.py (as bytes32).
     *
     * Reverts if the hash was already stored by anyone — ensuring each local
     * block is anchored at most once and the on-chain record is immutable.
     */
    function storeBlock(bytes32 blockHash) external {
        if (blockHash == bytes32(0)) revert ZeroHash();
        if (_records[blockHash].storedAt != 0) revert AlreadyStored(blockHash);

        _records[blockHash] = BlockRecord({
            blockHash: blockHash,
            storedAt:  block.timestamp,
            owner:     msg.sender
        });
        _ownerBlocks[msg.sender].push(blockHash);

        emit BlockStored(msg.sender, blockHash, block.timestamp);
    }

    // ── Read ──────────────────────────────────────────────────────────────────

    /**
     * @notice Check whether a block hash has been anchored, and by whom.
     * @param  blockHash  The bytes32 hash to look up.
     * @return exists     true if the hash was ever stored.
     * @return owner      Wallet address that stored it (zero if not found).
     * @return storedAt   Unix timestamp when it was stored (0 if not found).
     */
    function verifyBlock(bytes32 blockHash)
        external view
        returns (bool exists, address owner, uint256 storedAt)
    {
        BlockRecord storage r = _records[blockHash];
        return (r.storedAt != 0, r.owner, r.storedAt);
    }

    /**
     * @notice Return all block hashes anchored by a given wallet.
     * @param  owner  The wallet address to query.
     */
    function getOwnerBlocks(address owner)
        external view
        returns (bytes32[] memory)
    {
        return _ownerBlocks[owner];
    }

    /**
     * @notice How many hashes has `owner` anchored?
     */
    function getBlockCount(address owner) external view returns (uint256) {
        return _ownerBlocks[owner].length;
    }
}
