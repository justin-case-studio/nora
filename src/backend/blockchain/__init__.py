"""
Blockchain module for the Notarizer application.
"""
from .mintblue_client import MintBlueClient


def get_blockchain_client():
    """
    Factory function to create the blockchain client.
    Trial mode no longer uses a local/mock client, so we always return the real client.
    """
    client = MintBlueClient()
    print("[Blockchain] Using MintBlue client")
    return client


# Export the client and factory
__all__ = ['MintBlueClient', 'get_blockchain_client']
