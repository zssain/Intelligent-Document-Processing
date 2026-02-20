# Test Users

## Available Test Accounts

### Admin User
- **Email**: `admin@teclusion.ai`
- **Password**: `qwerty123`
- **UID**: `g7MRrHIQyGX7AfmsGcscHwPVuJA2`
- **Role**: `org_admin`
- **Clearance Level**: `3`
- **Tenant**: `default-tenant`
- **Permissions**: Full admin access to all features

### Regular User
- **Email**: `user@teclusion.ai`
- **Password**: `qwerty123`
- **UID**: `q2KvsryTWvU1uhLVrcqCC9XhE4S2`
- **Role**: `user`
- **Clearance Level**: `1`
- **Tenant**: `default-tenant`
- **Allowed Categories**: `general`
- **Permissions**: Basic user access

## How to Use

1. Start the frontend dev server:
   ```bash
   cd bluetide-ui
   npm run dev
   ```

2. Navigate to `http://localhost:3000/login`

3. Sign in with either test account

4. The auth system will:
   - Authenticate with Firebase
   - Extract custom claims (tenant_id, role, clearance_level)
   - Attach JWT token to all API requests
   - Apply route guards based on authentication

## Re-creating Users

If you need to recreate or update the test users:

```bash
cd functions
node create_test_users.js
```

To verify the users:

```bash
cd functions
node verify_test_users.js
```

## Custom Claims

Both users have custom JWT claims that are automatically included in their ID tokens:

- `tenant_id`: Multi-tenancy identifier
- `role`: User's role in the system
- `clearance_level`: Security clearance level (0-3)

These claims are validated by the backend on each API request.
