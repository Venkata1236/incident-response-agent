
# Clears the demo memory bank so you can re-seed cleanly.
# Not implemented yet: the delete-bank call has not been verified in the SDK docs.
# Until then, re-running seed_memory.py is safe because document_id makes retain idempotent,
# or simply change HINDSIGHT_BANK_ID in .env to start with a fresh empty bank.