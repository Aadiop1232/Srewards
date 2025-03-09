# config.py
TOKEN = "YOUR_BOT_TOKEN_HERE"  # Replace with your actual bot token
BOT_USERNAME = "ShadowRewardsBot"  # Without the '@'

# Hard-coded internal IDs for owners and admins.
# After a user registers, check their internal_id from the database and update these lists accordingly.
OWNERS = ["<owner_internal_id1>", "<owner_internal_id2>"]
ADMINS = ["<admin_internal_id1>", "<admin_internal_id2>"]

REQUIRED_CHANNELS = [
    "https://t.me/shadowsquad0",
    "https://t.me/Originlabs",
    "https://t.me/ShadowsquadHits",
    "https://t.me/Binhub_Originlabs"
]
