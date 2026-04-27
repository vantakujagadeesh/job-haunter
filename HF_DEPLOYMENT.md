# 🚀 Deploying to Hugging Face Spaces

This project is optimized for Hugging Face Spaces. Follow these steps to get your Real-time Job Auto Applier running in the cloud.

## 1. Create a New Space
- Go to [huggingface.co/new-space](https://huggingface.co/new-space)
- **Space Name**: `job-application-agent`
- **SDK**: `Streamlit`
- **Hardware**: `CPU Basic` (or better)
- **Visibility**: `Private` (Recommended since you'll store credentials)

## 2. Add Secrets (Crucial)
Go to **Settings** -> **Variables and secrets** -> **New secret** and add the following:

| Secret Name | Description |
|-------------|-------------|
| `OPENAI_API_KEY` | Your OpenAI API Key |
| `LINKEDIN_EMAIL` | Your LinkedIn Login Email |
| `LINKEDIN_PASSWORD` | Your LinkedIn Login Password |
| `SENDER_EMAIL` | Gmail address for notifications |
| `SENDER_PASSWORD` | Gmail App Password (16 characters) |
| `USER_EMAIL` | Your personal email to receive alerts |

## 3. Upload Files
Upload all the project files to the Space. The `packages.txt` will automatically install the necessary system dependencies for Playwright.

## 4. How the "Real-time" Mode Works
1. Go to the **⚡ Real-time Monitor** tab.
2. Enter your job search criteria.
3. Click **▶️ Start Monitoring**.
4. The system will now check for new jobs periodically and apply automatically to any that match your ATS threshold.

## 🛡️ Stealth & Security
The agent uses `playwright-stealth` and human-like delays to avoid detection. However, it is highly recommended to run this in a **Private Space** to protect your session data and credentials.
