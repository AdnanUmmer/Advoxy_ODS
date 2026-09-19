# Google Sign-In

Advoxy uses Google's official sign-in button and popup on `/login` and `/signup`.
The browser reads `NEXT_PUBLIC_GOOGLE_CLIENT_ID` and uses Google's official
Identity Services popup. The popup returns an ID token to `/api/auth/google/`;
Django verifies its audience against the backend-only `GOOGLE_CLIENT_ID` before
issuing the application's API token. The selected signup role and local booking
return URL are preserved. Existing accounts retain their role.

## Configuration

Set `NEXT_PUBLIC_GOOGLE_CLIENT_ID` in `frontend/.env.local` and set the same
Google Cloud **Web application** client ID as `GOOGLE_CLIENT_ID` in
`backend/.env`. Restart both servers after changing environment variables.
Set `NEXT_PUBLIC_GOOGLE_IDENTITY_SCRIPT_URL` to the Google Identity Services
script URL in the frontend environment template.

`GOOGLE_CLIENT_SECRET` must stay on the backend. The ID-token popup flow does
not require the secret; it is not sent to the browser.

In Google Cloud, add the exact frontend origins under **Authorized JavaScript origins**:

- `http://localhost:3000`
- `http://127.0.0.1:3000` if you use that hostname
- Your production HTTPS origin when deploying

Configure the consent screen and test users if the Google app is in testing.
This popup flow does not use `/accounts/google/login/callback/` as its callback.

Reference: https://developers.google.com/identity/gsi/web/guides/get-google-api-clientid

## Verify

1. Open `http://localhost:3000/login` and hard refresh after updating the app.
2. Click the official Google button and select a permitted Google account.
3. Confirm that you land on the dashboard, or the booking URL you started from.
4. Repeat from professional signup and confirm the new account has a professional profile.
5. Cancel the popup and confirm email sign-in remains available.

If Google reports an origin mismatch, check the exact scheme, hostname and port
in Authorized JavaScript origins. If the button cannot load, check browser
extensions and network access to `accounts.google.com`.

Regression tests mock Google's token verification; they do not prove a real
OAuth client or its Cloud configuration works. A real account sign-in is needed
to complete that check.
