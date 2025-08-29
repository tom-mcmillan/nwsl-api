# NWSL API Deployment Guide

## 🚀 Your API is Live!

Your NWSL API is now deployed and accessible at:
- **Direct Cloud Run URL**: https://nwsl-api-78453984015.us-central1.run.app
- **Custom Domain** (after DNS setup): https://api.nwsldata.com

## 📝 DNS Configuration Required

Add these DNS records to your domain (nwsldata.com):

### For api.nwsldata.com (direct to Cloud Run):
- **Type**: CNAME
- **Name**: api
- **Value**: ghs.googlehosted.com.

### For main site proxy (through Vercel):
Your Vercel site at nwsldata.com can proxy to the API using the vercel.json config.

## 🔗 Available Endpoints

Once DNS is configured, your API will be accessible at:

- **API Documentation**: https://api.nwsldata.com/docs (or https://nwsldata.com/docs via Vercel)
- **Alternative Docs**: https://api.nwsldata.com/redoc
- **Developer Registration**: https://api.nwsldata.com/register
- **API Endpoints**: https://api.nwsldata.com/api/v1/*

## 🎯 Two Access Options

### Option 1: Direct API Subdomain
- Users access: `api.nwsldata.com`
- Direct connection to Cloud Run
- Requires CNAME DNS record

### Option 2: Through Main Domain (Vercel Proxy)
- Users access: `nwsldata.com/api/*`
- Proxied through your Vercel site
- No additional DNS needed
- Uses the vercel.json rewrites

## 🔧 Management Commands

### Update the API:
```bash
# 1. Make changes to your code
# 2. Rebuild and deploy:
gcloud builds submit --tag gcr.io/nwsl-data/nwsl-api:latest .
gcloud run deploy nwsl-api --image gcr.io/nwsl-data/nwsl-api:latest --region us-central1
```

### View logs:
```bash
gcloud run logs read --service nwsl-api --region us-central1
```

### Check domain mapping status:
```bash
gcloud beta run domain-mappings list --region us-central1
```

## 🔑 API Authentication

All endpoints require an API key header:
- **Header**: `X-API-Key`
- **Demo Key**: `nwsl-demo-key-2024`
- **Get Real Key**: https://api.nwsldata.com/register

## 📊 Current Status

- ✅ API deployed to Cloud Run
- ✅ Database connected (Cloud SQL)
- ✅ Authentication system working
- ✅ Custom domain mapping created
- ⏳ Waiting for DNS propagation (can take 15-30 minutes)
- ⏳ SSL certificate provisioning (automatic after DNS is set)

## 🌐 CORS Configuration

The API is configured to accept requests from:
- https://nwsldata.com
- https://www.nwsldata.com
- http://localhost:3000 (for development)

## 💡 Next Steps

1. **Add DNS CNAME record** for api.nwsldata.com → ghs.googlehosted.com
2. **Wait 15-30 minutes** for DNS propagation
3. **Test the API** at https://api.nwsldata.com/health
4. **Deploy vercel.json** to your Vercel site if you want /api proxy

## 🛠 Troubleshooting

If the custom domain doesn't work after 30 minutes:
1. Check DNS propagation: `nslookup api.nwsldata.com`
2. Check certificate status: `gcloud beta run domain-mappings describe --domain api.nwsldata.com --region us-central1`
3. Ensure DNS record doesn't have trailing dot issues