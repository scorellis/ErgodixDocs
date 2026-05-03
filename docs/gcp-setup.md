# Google Cloud Platform Setup — One-Time SOP

This is the canonical setup playbook. Follow it once per ErgodixDocs install. End state: two credentials stored in your OS keyring (`google_oauth_client_id`, `google_oauth_client_secret`).

Total time: 10 minutes. Do not skip steps.

---

## Prerequisite

You have already run `./install_dependencies.sh` and `python auth.py status` works.

---

## Step 1. Sign in to Google Cloud Console

1. Open `https://console.cloud.google.com` in a browser.
2. Sign in with the **same Google account that owns your Tapestry Drive content**. For the canonical install this is `scorellis@gmail.com`.

---

## Step 2. Create the GCP project

1. At the top of the page, click the **project picker dropdown** (left of the search bar; shows "Select a project" or the name of your last project).
2. In the dialog that opens, click **NEW PROJECT** (top right of the dialog).
3. In the **Project name** field, type exactly: `ergodix`
4. Leave **Organization** as `No organization` (this is the default for personal Google accounts).
5. Leave **Location** as `No organization`.
6. Click **CREATE**.
7. Wait for the notification "Creating project: ergodix" to complete (~10 seconds). You will get a "Create Project: ergodix" success notification at the top right.
8. Click the notification, OR click the project picker dropdown again and select `ergodix`. The top bar must now show `ergodix` as the active project before you continue.

---

## Step 3. Enable the Google Drive API

1. Click the hamburger menu (three horizontal lines, top left).
2. Hover over **APIs & Services**.
3. Click **Library**.
4. In the search box on the Library page, type exactly: `Google Drive API`
5. Click the search result titled **Google Drive API** (the icon is the green/yellow/blue Drive triangle).
6. Click the **ENABLE** button.
7. Wait for the page to redirect to the API's overview page. The button should now say **MANAGE** instead of **ENABLE**.

---

## Step 4. Enable the Google Docs API

1. Click the hamburger menu (top left).
2. Hover over **APIs & Services**.
3. Click **Library**.
4. In the search box, type exactly: `Google Docs API`
5. Click the search result titled **Google Docs API**.
6. Click the **ENABLE** button.
7. Wait for redirect. The button should now say **MANAGE**.

---

## Step 5. Configure the OAuth consent screen

1. Click the hamburger menu (top left).
2. Hover over **APIs & Services**.
3. Click **OAuth consent screen**.
4. Under **User Type**, select the **External** radio button.
5. Click the **CREATE** button.

You are now on the "Edit app registration" page, screen 1 of 4 (App information).

6. In the **App name** field, type exactly: `ErgodixDocs`
7. In the **User support email** dropdown, select your gmail address (the only option).
8. Scroll down to **Developer contact information**.
9. In the **Email addresses** field, type your gmail address.
10. Click **SAVE AND CONTINUE** at the bottom.

You are now on screen 2 of 4 (Scopes).

11. Do **not** click "Add or Remove Scopes." Scroll past everything.
12. Click **SAVE AND CONTINUE** at the bottom.

You are now on screen 3 of 4 (Test users).

13. Click **+ ADD USERS**.
14. In the dialog, type your gmail address. Press Enter or click outside the field.
15. Click **ADD** at the bottom of the dialog.
16. Click **SAVE AND CONTINUE** at the bottom of the page.

You are now on screen 4 of 4 (Summary).

17. Scroll to the bottom and click **BACK TO DASHBOARD**.

You should now see the OAuth consent screen dashboard with `ErgodixDocs` listed and **Publishing status: Testing**. Leave it in Testing — that is correct.

---

## Step 6. Create the OAuth client ID and secret

1. Click the hamburger menu (top left).
2. Hover over **APIs & Services**.
3. Click **Credentials**.
4. Near the top of the page, click **+ CREATE CREDENTIALS**.
5. In the dropdown that appears, click **OAuth client ID**.
6. Under **Application type**, click the dropdown and select **Desktop app**. (Do not pick Web application or any other option.)
7. In the **Name** field, type exactly: `ErgodixDocs CLI`
8. Click **CREATE** at the bottom.

A modal titled **OAuth client created** will appear.

9. Click the **copy icon** next to **Client ID**. Paste the value into a temporary scratch location (a new email draft, a TextEdit window — anywhere not committed to git). It will look like: `123456789012-aBcDeFgHiJ....apps.googleusercontent.com`
10. Click the **copy icon** next to **Client secret**. Paste it into the same scratch location. It will look like: `GOCSPX-AbCdEfGhIjKlMnOp` (about 35 characters starting with `GOCSPX-`).
11. Click **OK** to close the modal.

You should now see your client listed under "OAuth 2.0 Client IDs" with type **Desktop**.

---

## Step 7. Store the credentials in the OS keyring

In your terminal, from the ErgodixDocs repo directory:

1. Activate the virtual environment if it is not already active:
   ```bash
   source .venv/bin/activate
   ```
2. Store the client ID:
   ```bash
   python auth.py set-key google_oauth_client_id
   ```
   When prompted, paste the client ID value from your scratch location. The input is hidden — you will not see it. Press **Enter**.

3. If macOS shows a Keychain dialog "Python wants to use the 'login' keychain," click **Always Allow**.

4. Store the client secret:
   ```bash
   python auth.py set-key google_oauth_client_secret
   ```
   Paste the client secret. Press **Enter**.

5. Verify both are stored:
   ```bash
   python auth.py status
   ```
   The output must show `✓` next to both `google_oauth_client_id` and `google_oauth_client_secret`, with the source listed as `keyring`. If either shows `✗`, repeat steps 2 or 4.

6. Delete the scratch location where you pasted the values (close the email draft, clear the TextEdit window). The values are now in the keyring; the scratch copy is unnecessary and is a leak surface.

---

## Step 8. Confirm done

Reply **"GCP done"** to the next conversation prompt, OR if you encounter any error, paste the exact error message verbatim.

You will not see the GCP console again unless you need to rotate the secret, add another redirect URI, or add another test user.

---

## Notes for future implementors

- **Why External and not Internal**: Internal is for Google Workspace organizations only. A personal `@gmail.com` account cannot use Internal.
- **Why Desktop app and not Web application**: Desktop app uses the OAuth "installed app" flow, which is the right pattern for a CLI tool that opens a browser for consent. Web application requires a registered redirect URI and is for server-side apps.
- **Why no scopes added on the consent screen**: scopes are declared at runtime by `auth.py` (`drive.readonly` + `documents.readonly`). Listing them on the consent screen is only required when an app is published (out of Testing). Since this app stays in Testing forever for a single-author install, this step is unnecessary.
- **First-time OAuth browser flow**: when `ergodix migrate` runs for the first time, your browser will show "Google hasn't verified this app." This is expected for a Desktop OAuth client in Testing mode. Click **Advanced** → **Go to ErgodixDocs (unsafe)** → grant the requested read-only scopes. The refresh token is then stored at `<repo>/.ergodix_tokens.json` and the browser flow does not repeat.
- **Rotation**: to rotate the client secret, return to **APIs & Services → Credentials**, click your OAuth 2.0 Client ID, click **+ ADD SECRET**, copy the new secret, store it via `python auth.py set-key google_oauth_client_secret`, then delete the old secret in the console.
- **Adding more test users**: APIs & Services → OAuth consent screen → **Test users** section → **+ ADD USERS**. Required if a collaborator (e.g. an editor) wants to run their own ErgodixDocs install against the same project. Each test user must be added by gmail address before they can authorize.
