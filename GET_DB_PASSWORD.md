# Get Database Password

## Almost Done! 🎯

I've set 4 out of 5 environment variables. Just need the database password!

## Get Database Password

1. Go to: https://supabase.com/dashboard/project/gxpcrohsbtndndypagie

2. Go to: **Project Settings** → **Database**

3. Under **Connection string**, you'll see the password in the URI
   - Or click **Reset database password** if you need to set a new one
   - Copy the full connection string (it includes the password)

4. Share the **full DATABASE_URL** with the password included, like:
   ```
   postgresql://postgres:ACTUAL_PASSWORD_HERE@db.gxpcrohsbtndndypagie.supabase.co:5432/postgres
   ```

**Or** if you prefer, I can help you reset the password and generate a new one.

---

Once I have this, I'll:
- Set the DATABASE_URL environment variable
- Set CHROMADB_PATH (for where ChromaDB data will be stored)
- Deploy to Vercel! 🚀

