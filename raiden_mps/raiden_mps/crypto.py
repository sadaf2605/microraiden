"""
Convention within this module is to only add the '0x' hex prefix to addresses while other
hex-encoded values, such as hashes and private keys, come without a 0x prefix.
"""

from coincurve import PrivateKey, PublicKey
from eth_utils import encode_hex, decode_hex, remove_0x_prefix, keccak, to_normalized_address


def equal_addrs(addr1: str, addr2: str) -> bool:
    return to_normalized_address(addr1) == to_normalized_address(addr2)


def generate_privkey() -> bytes:
    return encode_hex(PrivateKey().secret)


def pubkey_to_addr(pubkey) -> str:
    if isinstance(pubkey, PublicKey):
        pubkey = pubkey.format(compressed=False)
    assert isinstance(pubkey, bytes)
    return encode_hex(sha3(pubkey[1:])[-20:])


def privkey_to_addr(privkey: str) -> str:
    return pubkey_to_addr(PrivateKey.from_hex(remove_0x_prefix(privkey)).public_key)


def addr_from_sig(sig, msg):
    # Support legacy EC v value of 27.
    if sig[-1] >= 27:
        sig = sig[:-1] + bytes([sig[-1] - 27])

    receiver_pubkey = PublicKey.from_signature_and_message(sig, msg, hasher=None)
    return pubkey_to_addr(receiver_pubkey)


def sha3(*args) -> bytes:
    """
    Simulates Solidity's sha3 function. Integers can be passed as tuples where the second tuple
    element specifies the variable's size in bits, e.g.:
    sha3((5, 32))
    would be equivalent to Solidity's
    sha3(uint32(5))
    Default size is 256.
    """

    def format_int(value, size):
        if value >= 0:
            return decode_hex('{:x}'.format(value).zfill(size // 4))
        else:
            return decode_hex('{:x}'.format((1 << size) + value))

    msg = b''
    for arg in args:
        if isinstance(arg, bytes):
            msg += arg
        elif isinstance(arg, str):
            if arg[:2] == '0x':
                msg += decode_hex(arg[2:])
            else:
                msg += arg.encode()
        elif isinstance(arg, int):
            msg += format_int(arg, 256)
        elif isinstance(arg, tuple):
            msg += format_int(arg[0], arg[1])
        else:
            raise ValueError('Unsupported type: {}.'.format(type(arg)))

    return keccak(msg)


def sha3_hex(*args) -> bytes:
    return encode_hex(sha3(*args))


def sign(privkey: str, msg: bytes) -> bytes:
    pk = PrivateKey.from_hex(remove_0x_prefix(privkey))
    assert len(msg) == 32

    sig = pk.sign_recoverable(msg, hasher=None)
    assert len(sig) == 65

    sig = sig[:-1] + chr(sig[-1]).encode()

    return sig


def balance_message_hash(
        receiver: str, open_block_number: int, balance: int, contract_address: str
) -> bytes:
    return sha3(receiver, (open_block_number, 32), (balance, 192), contract_address)


def sign_balance_proof(
        privkey: str, receiver: str, open_block_number: int, balance: int, contract_address: str
) -> bytes:
    msg = balance_message_hash(receiver, open_block_number, balance, contract_address)
    return sign(privkey, msg)


def verify_balance_proof(
        receiver: str,
        open_block_number: int,
        balance: int,
        balance_sig: bytes,
        contract_address: str
) -> str:
    msg = balance_message_hash(receiver, open_block_number, balance, contract_address)
    return addr_from_sig(balance_sig, msg)


def closing_agreement_message_hash(balance_sig: bytes) -> bytes:
    return sha3(balance_sig)


def sign_close(privkey: str, balance_sig: bytes) -> bytes:
    msg = closing_agreement_message_hash(balance_sig)
    closing_sig = sign(privkey, msg)

    return closing_sig


def verify_closing_signature(balance_sig: bytes, closing_sig: bytes) -> str:
    msg = closing_agreement_message_hash(balance_sig)
    return addr_from_sig(closing_sig, msg)