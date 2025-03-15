# config.py

# Bot settings
TOKEN = "7760154469:AAFwBrol9EP2L78Wt0sTqXcoz3OiL4HPy8I"
BOT_USERNAME = "ShadowRewardsBot"  # without the '@' symbol

# Required channels users must join
REQUIRED_CHANNELS = [
    "https://t.me/shadowsquad0",
    "https://t.me/Originlabs",
    "https://t.me/ShadowsquadHits",
    "https://t.me/Binhub_Originlabs"
]

# Owners and Admins (Telegram IDs as strings)
OWNERS = ["7218606355", "5822279535", "5933410316", "6355646303"]
ADMINS = ["6061298481", "1572380763"]

# Logs channel where bot events will be posted (bot must be added with full privileges)
LOGS_CHANNEL = "@ShadowBotLogs"

# MongoDB connection settings
MONGO_URI = "mongodb://localhost:27017/"  # Change if using a remote MongoDB instance
MONGO_DB_NAME = "shadow_rewards_db"

# Default dynamic configuration values (will be stored/updated in MongoDB)
DEFAULT_ACCOUNT_CLAIM_COST = 2   # Points required to claim an account
DEFAULT_REFERRAL_BONUS = 4       # Points awarded per successful referral
