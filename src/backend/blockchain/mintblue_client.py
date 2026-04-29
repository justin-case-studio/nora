"""
MintBlue API client for the Notarizer application.
Handles blockchain transactions using the MintBlue API.
"""
import os
import sys
import time
import requests
import json
from datetime import datetime, timezone

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from database.repositories import SettingsRepository


class MintBlueClient:
    """Client for interacting with the MintBlue API."""

    def __init__(self):
        """Initialize the MintBlue client."""
        self.settings_repo = SettingsRepository()
        # SDK access token used for authentication
        self.sdk_token = self.settings_repo.get_api_key()
        # Alias for backward compatibility (other components may still access .api_key)
        self.api_key = self.sdk_token
        self.project_id = self.settings_repo.get_project_id()
        # Use JSON-RPC endpoint as per MintBlue documentation
        self.base_url = "https://api.mintblue.com/sdk/latest"
        # WhatsOnChain BSV explorer used for verification. MintBlue's getTransaction
        # does not reliably backfill confirmation state, so verification reads
        # straight from the chain instead.
        self.woc_base_url = "https://api.whatsonchain.com/v1/bsv/main"
        # Timeout for the outgoing HTTPS request (MintBlue can take ~45s for the
        # first TX of a session). 90 s provides head-room yet still fails fast
        # enough for UI feedback.
        self.timeout = 90  # seconds

    def set_credentials(self, sdk_token, project_id):
        """Set the API credentials."""
        self.sdk_token = sdk_token
        self.api_key = sdk_token  # keep alias in sync
        self.project_id = project_id

    def create_transaction(self, hash_value):
        """
        Create a transaction with the hash value.

        Args:
            hash_value: SHA-256 hash to store in the transaction

        Returns:
            Transaction ID if successful, None otherwise
        """
        print("Creating transaction for hash: {}...".format(hash_value[:8]))

        if not self.sdk_token or not self.project_id:
            error_msg = "SDK token or project ID not set"
            print("❌ [MintBlueClient] {}".format(error_msg))
            raise ValueError(error_msg)

        # Validate hash format
        if not isinstance(hash_value, str) or len(hash_value) != 64:
            error_msg = "Invalid hash format: {}".format(hash_value)
            print("❌ [MintBlueClient] {}".format(error_msg))
            raise ValueError(error_msg)

        outputs = [
            {
                "type": "data",
                "value": hash_value,
                "sign": True,
            }
        ]

        params = {
            "project_id": self.project_id,
            "outputs": outputs
        }

        print("[MintBlueClient] Calling createTransaction via JSON-RPC …")

        try:
            result = self._rpc_request("createTransaction", params)
            tx_id = result.get("txid") or result.get("tx_id")
            print("Transaction created successfully. TX ID: {}".format(tx_id))
            return tx_id

        except requests.exceptions.RequestException as e:
            # Handle network errors
            error_msg = "Failed to connect to MintBlue API: {}".format(str(e))
            print("❌ [MintBlueClient] {}".format(error_msg))
            raise ConnectionError(error_msg)

        except RuntimeError as e:
            print("❌ [MintBlueClient] {}".format(str(e)))
            raise

        except json.JSONDecodeError:
            # Handle invalid JSON response
            error_msg = "Invalid response from MintBlue API"
            print("❌ [MintBlueClient] {}".format(error_msg))
            raise ValueError(error_msg)

    def verify_transaction(self, tx_id, expected_hash):
        """
        Verify a transaction contains the expected hash, by reading directly
        from the BSV chain via WhatsOnChain. MintBlue's own getTransaction
        does not reliably populate confirmed_at/block for confirmed txs.

        Args:
            tx_id: Transaction ID to verify
            expected_hash: Expected SHA-256 hash

        Returns:
            Dictionary with verification results
        """
        if not isinstance(tx_id, str) or not tx_id:
            raise ValueError("Invalid tx_id")
        if not isinstance(expected_hash, str) or len(expected_hash) != 64:
            raise ValueError("Invalid hash format: {}".format(expected_hash))

        url = "{}/tx/hash/{}".format(self.woc_base_url, tx_id)
        print("[MintBlueClient] Verifying via WhatsOnChain: {}".format(url))

        response = self._woc_get(url)

        if response.status_code == 404:
            return {
                "status": "failed",
                "message": "Transaction not found on BSV",
                "confirmed": False,
                "hash_match": False,
                "timestamp": None,
                "project_id": None,
            }

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise RuntimeError("WhatsOnChain HTTP error: {}".format(e))

        try:
            tx_data = response.json()
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON from WhatsOnChain API")

        hash_match = self._hash_in_op_return(tx_data, expected_hash)
        if not hash_match:
            return {
                "status": "failed",
                "message": "Hash not found in transaction OP_RETURN",
                "confirmed": False,
                "hash_match": False,
                "timestamp": None,
                "project_id": None,
            }

        confirmations = tx_data.get("confirmations") or 0
        if confirmations < 1:
            return {
                "status": "pending",
                "message": "Transaction broadcast but not yet confirmed in a block",
                "confirmed": False,
                "hash_match": True,
                "timestamp": None,
                "project_id": None,
            }

        blocktime = tx_data.get("blocktime")
        timestamp = (
            datetime.fromtimestamp(blocktime, tz=timezone.utc).isoformat()
            if blocktime else None
        )

        return {
            "status": "verified",
            "message": "Transaction verified successfully",
            "confirmed": True,
            "hash_match": True,
            "timestamp": timestamp,
            "project_id": None,
            "block_height": tx_data.get("blockheight"),
            "tx_id": tx_id,
        }

    def _woc_get(self, url):
        """
        GET against WhatsOnChain with bounded retries on 429 and 5xx.
        Honours Retry-After but caps each wait so the verify UI stays responsive.
        """
        max_attempts = 3
        backoff = 1
        cap = 5  # seconds per wait, total wait < ~10s
        for attempt in range(1, max_attempts + 1):
            try:
                response = requests.get(url, timeout=self.timeout)
            except requests.exceptions.RequestException as e:
                if attempt >= max_attempts:
                    raise ConnectionError("Failed to connect to WhatsOnChain API: {}".format(e))
                print("[MintBlueClient] WoC network error attempt {}: {}".format(attempt, e))
                time.sleep(backoff)
                backoff = min(backoff * 2, cap)
                continue

            if response.status_code == 429 or response.status_code in (500, 502, 503, 504):
                if attempt >= max_attempts:
                    return response
                wait = backoff
                retry_after = response.headers.get("Retry-After")
                if retry_after:
                    try:
                        wait = max(wait, int(retry_after))
                    except ValueError:
                        pass
                wait = min(wait, cap)
                print("[MintBlueClient] WoC HTTP {}; retrying in {}s (attempt {}/{})".format(
                    response.status_code, wait, attempt, max_attempts))
                time.sleep(wait)
                backoff = min(backoff * 2, cap)
                continue

            return response

        raise ConnectionError("WhatsOnChain retry loop exhausted")

    @staticmethod
    def _hash_in_op_return(tx_data, expected_hash):
        """Return True if expected_hash appears in any OP_RETURN output of tx_data."""
        ascii_hex = expected_hash.encode("ascii").hex()
        for vout in tx_data.get("vout", []) or []:
            script = vout.get("scriptPubKey") or {}
            if script.get("type") != "nulldata":
                continue
            op_return = script.get("opReturn") or {}
            for part in op_return.get("parts") or []:
                if part and expected_hash in part:
                    return True
            if ascii_hex in (script.get("hex") or ""):
                return True
        return False

    def test_connection(self):
        """
        Test the connection to the MintBlue API.

        Returns:
            True if successful, False otherwise
        """
        if not self.sdk_token:
            return False

        try:
            # call getProjects
            result = self._rpc_request("getProjects", {})
            if self.project_id:
                project_ids = [p.get("id") for p in result.get("projects", [])]
                return self.project_id in project_ids
            return True
        except Exception:
            return False

    # --- Internal helper for JSON-RPC requests ---
    def _rpc_request(self, method, params):
        """Send JSON-RPC request to MintBlue server."""
        if not self.sdk_token:
            raise ValueError("SDK token not set")

        # Use the *full* SDK access token for authentication (MintBlue no longer
        # requires the historic "secret-token:mintblue.com/sdk/<secret>" format).
        # If problems persist we can switch back, but the public docs appear to
        # be outdated – using the full token avoids the 500 SubtleCrypto digest
        # error seen in practice.

        headers = {
            "Content-Type": "application/json",
            "mintblue-sdk-token": self.sdk_token
        }

        payload = {
            "id": "1",
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }

        attempt = 1
        max_attempts = 3
        backoff = 3  # seconds between retries
        while True:
            try:
                start_t = time.time()
                response = requests.post(
                    self.base_url,
                    headers=headers,
                    data=json.dumps(payload),
                    timeout=self.timeout
                )
                elapsed = time.time() - start_t
                print(f"[MintBlueClient] {method} HTTP call completed in {elapsed:.1f}s (status {response.status_code})")

                # Retry on 502/503/504 upstream issues
                if response.status_code in (502, 503, 504) and attempt < max_attempts:
                    print(f"[MintBlueClient] Transient HTTP {response.status_code}. Retrying in {backoff}s (attempt {attempt}/{max_attempts}) …")
                    time.sleep(backoff)
                    attempt += 1
                    backoff *= 2  # Exponential back-off
                    continue

                break  # Either success or non-retryable status

            except requests.exceptions.RequestException as e:
                print(f"❌ [MintBlueClient] Network error on attempt {attempt}: {e}")
                if attempt >= max_attempts:
                    raise
                time.sleep(backoff)
                attempt += 1
                backoff *= 2
                continue

        # Log non-200 HTTP responses with body for easier debugging before raising
        if response.status_code != 200:
            print(
                f"❌ [MintBlueClient] HTTP {response.status_code} when calling {method}. "
                f"Response body: {response.text[:500]}"
            )

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as http_err:
            # Already logged above, but include status code & reason
            print(f"❌ [MintBlueClient] HTTP error: {http_err}")
            raise

        # Attempt to parse JSON. If this fails, print raw text.
        try:
            result_json = response.json()
        except json.JSONDecodeError:
            print(
                f"❌ [MintBlueClient] Failed to decode JSON response from {method}. "
                f"Raw response: {response.text[:500]}"
            )
            raise

        # Check for JSON-RPC error object
        if "error" in result_json:
            print(f"❌ [MintBlueClient] RPC error from {method}: {result_json['error']}")
            raise RuntimeError(f"MintBlue RPC error: {result_json['error']}")

        return result_json.get("result")
