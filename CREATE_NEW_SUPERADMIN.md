# Creating a New Superadmin for aiodcounter05

## Step-by-Step Guide

### Step 1: Create User in Firebase Console

1. **Go to Firebase Authentication:**
   - Visit: https://console.firebase.google.com/project/aiodcounter05/authentication/users
   - Click "Add user"

2. **Enter new superadmin details:**
   - Email: `[YOUR_NEW_EMAIL]` (e.g., `admin@yourdomain.com`)
   - Password: `[CREATE_STRONG_PASSWORD]`
   - Click "Add user"

3. **Copy the UID:**
   - After creating, find the new user in the list
   - **Copy the UID** (you'll need this for the next step)

### Step 2: Set Custom Claims

1. **Still in Authentication Users page:**
   - Click on the newly created user
   - Scroll down to "Custom claims"
   - Click "Edit"
   - Add this JSON:
   ```json
   {"role": "superadmin", "admin": true, "superadmin": true}
   ```
   - Click "Save"

### Step 3: Create Firestore Document

1. **Go to Firestore:**
   - Visit: https://console.firebase.google.com/project/aiodcounter05/firestore

2. **Navigate to tenants collection:**
   - Click on `tenants`
   - Click on the first tenant document (or create one called "default" if none exist)

3. **Create/navigate to users subcollection:**
   - Inside the tenant document, look for `users` subcollection
   - If it doesn't exist, click "Start collection" and name it `users`

4. **Add the superadmin user document:**
   - Click "Add document"
   - **Document ID**: Paste the UID you copied in Step 1
   - Add these fields:
     - `email` (string): `[YOUR_NEW_EMAIL]`
     - `role` (string): `superadmin`
     - `status` (string): `active`
     - `displayName` (string): `Super Admin` (optional)
     - `createdAt` (timestamp): Use current time
     - `updatedAt` (timestamp): Use current time
   - Click "Save"

### Step 4: Test Login

1. **Go to the app:**
   - Visit: https://aiodcounter05.web.app/

2. **Sign in:**
   - Use the new email and password you created
   - You should be automatically redirected to `/Superadmin`
   - You should see the Superadmin dashboard (not a white page!)

### Step 5: Clean Up Old Account (Optional)

Once the new superadmin is working, you can delete the old `zymer4him@gmail.com` account:
1. Go to Authentication Users
2. Find `zymer4him@gmail.com`
3. Click the three dots → Delete user

## Troubleshooting

If you still see a white page:
1. Make sure you created the Firestore document with the EXACT UID from Authentication
2. Make sure `status` is `active` (not "pending")
3. Make sure `role` is `superadmin`
4. Sign out and sign back in
5. Try in an incognito/private window
6. Check browser console (F12) for errors

## Alternative: Use Existing Email

If you want to keep using `zymer4him@gmail.com`:
1. Get the UID from Authentication
2. Create the Firestore document as described in Step 3
3. Make sure custom claims are set (Step 2)
4. Sign out and sign back in
