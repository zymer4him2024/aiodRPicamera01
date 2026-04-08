# Fix Superadmin Access for aiodcounter05

## Problem
You can't log in because you need superadmin approval, but you can't approve yourself because you can't access the Superadmin page. This is a chicken-and-egg problem.

## Solution: Bootstrap the First Superadmin

### Option 1: Using Firebase Console (EASIEST - DO THIS)

1. **Go to Firestore Database**
   - Visit: https://console.firebase.google.com/project/aiodcounter05/firestore
   
2. **Create the user document**
   - Click "Start collection"
   - Collection ID: `tenants`
   - Document ID: `default`
   - Click "Next"
   
3. **Add a subcollection**
   - In the `default` document, click "Start collection"
   - Collection ID: `users`
   - Document ID: (your Firebase Auth UID - see step 4)
   
4. **Get your Firebase Auth UID**
   - Open new tab: https://console.firebase.google.com/project/aiodcounter05/authentication/users
   - Find `zymer4him@gmail.com`
   - Copy the UID (looks like: `abc123def456...`)
   
5. **Create the user document with these fields**
   ```
   email: zymer4him@gmail.com
   role: superadmin
   status: active
   createdAt: (timestamp - use "Add field" > "timestamp")
   updatedAt: (timestamp - use "Add field" > "timestamp")
   ```

6. **Set Custom Claims in Authentication**
   - Go to: https://console.firebase.google.com/project/aiodcounter05/authentication/users
   - Click on `zymer4him@gmail.com`
   - Scroll down to "Custom claims"
   - Click "Edit"
   - Add this JSON:
   ```json
   {"role": "superadmin", "admin": true, "superadmin": true}
   ```
   - Click "Save"

7. **Test**
   - If you're logged in to aiodcounter05.web.app, SIGN OUT first
   - Go to: https://aiodcounter05.web.app/
   - Sign in with `zymer4him@gmail.com`
   - You should be redirected to /admin or /Superadmin

### Option 2: Using the Bootstrap Script (If you have gcloud access)

1. **Authenticate with gcloud**
   ```bash
   gcloud auth application-default login
   ```
   Complete the browser authentication and make sure to check ALL the permission boxes.

2. **Run the bootstrap script**
   ```bash
   cd /Users/shawnshlee/1_Antigravity/1_Antig_aiodcounter01
   node bootstrap-superadmin.js
   ```

3. **Sign out and sign back in**
   - Go to https://aiodcounter05.web.app/
   - Sign out if logged in
   - Sign in with `zymer4him@gmail.com`

### Option 3: Using Service Account Key

1. **Download service account key**
   - Go to: https://console.firebase.google.com/project/aiodcounter05/settings/serviceaccounts/adminsdk
   - Click "Generate new private key"
   - Save as `aiodcounter05-service-account.json`

2. **Update the bootstrap script**
   Edit `bootstrap-superadmin.js` and add at the top:
   ```javascript
   const serviceAccount = require('./aiodcounter05-service-account.json');
   
   admin.initializeApp({
     credential: admin.credential.cert(serviceAccount),
     projectId: 'aiodcounter05'
   });
   ```

3. **Run the script**
   ```bash
   node bootstrap-superadmin.js
   ```

## Verification

After completing any of the above options:

1. Sign out of aiodcounter05.web.app (if logged in)
2. Sign in with `zymer4him@gmail.com`
3. You should see the admin/superadmin dashboard
4. If you still see a white page, check the browser console (F12) for errors

## Troubleshooting

If you still can't access the Superadmin page after these steps:
- Check browser console for JavaScript errors
- Verify the Firestore document was created correctly
- Verify custom claims were set in Authentication
- Try clearing browser cache and cookies
- Try in an incognito/private window
