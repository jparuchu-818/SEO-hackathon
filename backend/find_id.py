# backend/find_id.py
import requests

# 🔑 PASTE YOUR API KEY HERE
GAMMA_API_KEY = "sk-gamma-cF7gkWjTtcG3lO1zMbUKiV6QzhxW8pcd1B3pfKfFI"

def find_my_workspace_id():
    """
    Connects to the Gamma API to find and print your Workspace ID.
    """
    if not GAMMA_API_KEY or "sk-gamma-" not in GAMMA_API_KEY:
        print("🚨 Error: Please paste your valid Gamma API key into the script.")
        return

    # FIX: Corrected the API endpoint URL. This is the only line that changed.
    endpoint = "https://api.gamma.app/workspaces"
    headers = {"Authorization": f"Bearer {GAMMA_API_KEY}"}

    print("🔎 Asking Gamma for your Workspace ID...")
    
    try:
        response = requests.get(endpoint, headers=headers)
        response.raise_for_status()  # Check for errors
        
        data = response.json()
        workspaces = data.get("workspaces", [])
        
        if not workspaces:
            print("❌ No workspaces found for this API key.")
            return
            
        first_workspace_id = workspaces[0].get("id")
        
        print("\n" + "="*40)
        print("✅ SUCCESS! Your Workspace ID is:")
        print(first_workspace_id)
        print("="*40 + "\n")
        print("📋 Now, copy the ID above and paste it into the")
        print("   `GAMMA_WORKSPACE_ID` variable in the `combine_results.py` script.")

    except requests.exceptions.HTTPError as e:
        print(f"🚨 An error occurred. Status Code: {e.response.status_code}")
        if e.response.status_code == 401:
            print("   This means your API key is likely invalid or expired.")
        print("   Response:", e.response.text)
    except Exception as e:
        print(f"🚨 A general error occurred: {e}")

if __name__ == "__main__":
    find_my_workspace_id()