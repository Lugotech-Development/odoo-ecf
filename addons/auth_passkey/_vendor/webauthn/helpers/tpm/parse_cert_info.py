from ..exceptions import InvalidTPMCertInfoStructure
from .structs import (
    TPM_ST,
    TPM_ST_MAP,
    TPMCertInfo,
    TPMCertInfoAttested,
    TPMCertInfoClockInfo,
)


def parse_cert_info(val: bytes) -> TPMCertInfo:
    """
    Turn `response.attestationObject.attStmt.certInfo` into structured data
    """
    pointer = 0

    # The constant "TPM_GENERATED_VALUE" indicating a structure generated by TPM
    magic_bytes = val[pointer : pointer + 4]
    pointer += 4

    # Type of the cert info structure
    type_bytes = val[pointer : pointer + 2]
    pointer += 2
    mapped_type = TPM_ST_MAP[type_bytes]

    # Name of parent entity
    qualified_signer_length = int.from_bytes(val[pointer : pointer + 2], "big")
    pointer += 2
    qualified_signer = val[pointer : pointer + qualified_signer_length]
    pointer += qualified_signer_length

    # Expected hash value of `attsToBeSigned`
    extra_data_length = int.from_bytes(val[pointer : pointer + 2], "big")
    pointer += 2
    extra_data_bytes = val[pointer : pointer + extra_data_length]
    pointer += extra_data_length

    # Info about the TPM's internal clock
    clock_info_bytes = val[pointer : pointer + 17]
    pointer += 17

    # Device firmware version
    firmware_version_bytes = val[pointer : pointer + 8]
    pointer += 8

    # Verify that type is set to TPM_ST_ATTEST_CERTIFY.
    if mapped_type != TPM_ST.ATTEST_CERTIFY:
        raise InvalidTPMCertInfoStructure(
            f'Cert Info type "{mapped_type}" was not "{TPM_ST.ATTEST_CERTIFY}"'
        )

    # Attested name
    attested_name_length = int.from_bytes(val[pointer : pointer + 2], "big")
    pointer += 2
    attested_name_bytes = val[pointer : pointer + attested_name_length]
    pointer += attested_name_length
    qualified_name_length = int.from_bytes(val[pointer : pointer + 2], "big")
    pointer += 2
    qualified_name_bytes = val[pointer : pointer + qualified_name_length]
    pointer += qualified_name_length

    return TPMCertInfo(
        magic=magic_bytes,
        type=mapped_type,
        extra_data=extra_data_bytes,
        attested=TPMCertInfoAttested(attested_name_bytes, qualified_name_bytes),
        # Note that the remaining fields in the "Standard Attestation Structure"
        # [TPMv2-Part1] section 31.2, i.e., qualifiedSigner, clockInfo and
        # firmwareVersion are ignored. These fields MAY be used as an input to risk
        # engines.
        qualified_signer=qualified_signer,
        clock_info=TPMCertInfoClockInfo(clock_info_bytes),
        firmware_version=firmware_version_bytes,
    )
