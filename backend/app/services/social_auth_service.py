import os
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from dotenv import load_dotenv
from urllib.parse import urlencode
import httpx
import logging
load_dotenv()
logger = logging.getLogger(__name__)
class SocialAuthService:
    def __init__(self):
        self.INSTAGRAM_CLIENT_ID = os.getenv('INSTAGRAM_CLIENT_ID')
        self.INSTAGRAM_CLIENT_SECRET = os.getenv('INSTAGRAM_CLIENT_SECRET')
        self.INSTAGRAM_REDIRECT_URI = os.getenv('INSTAGRAM_REDIRECT_URI')
        self.META_APP_ID = os.getenv('META_APP_ID')
        self.META_APP_SECRET = os.getenv('META_APP_SECRET')
        self.META_CONFIG_ID = os.getenv('META_CONFIG_ID')
        self.META_GRAPH_VERSION = os.getenv('META_GRAPH_VERSION', 'v24.0')
        
    def get_instagram_auth_url(self, state: str) -> str:
        """Construit l'URL d'autorisation pour le flux Instagram Business."""
        if not self.INSTAGRAM_CLIENT_ID or not self.INSTAGRAM_REDIRECT_URI:
            raise HTTPException(status_code=500, detail='Instagram auth is not configured on the server.')
        scopes = ['instagram_business_basic', 'instagram_business_manage_messages']
        logger.info(f"🔍 DEBUG get_instagram_auth_url - scopes: {scopes}")
        logger.info(f"🔍 DEBUG get_instagram_auth_url - client_id: {self.INSTAGRAM_CLIENT_ID}")
        logger.info(f"🔍 DEBUG get_instagram_auth_url - redirect_uri: {self.INSTAGRAM_REDIRECT_URI}")
        logger.info(f"🔍 DEBUG get_instagram_auth_url - state: {state}")
        params = {'client_id': self.INSTAGRAM_CLIENT_ID, 'redirect_uri': self.INSTAGRAM_REDIRECT_URI, 'scope': ','.join(scopes), 'response_type': 'code', 'state': state}
        auth_url = f'https://api.instagram.com/oauth/authorize?{urlencode(params)}'
        return auth_url


    async def handle_instagram_callback(self, code: str) -> dict:
        """Échange le code d'autorisation contre un token d'accès longue durée."""
        if not self.INSTAGRAM_CLIENT_ID or not self.INSTAGRAM_CLIENT_SECRET or not self.INSTAGRAM_REDIRECT_URI:
            raise HTTPException(status_code=500, detail='Instagram auth is not configured on the server.')
        async with httpx.AsyncClient() as client:
            try:
                short_lived_token_url = 'https://api.instagram.com/oauth/access_token'
                short_lived_payload = {'client_id': self.INSTAGRAM_CLIENT_ID, 'client_secret': self.INSTAGRAM_CLIENT_SECRET, 'grant_type': 'authorization_code', 'redirect_uri': self.INSTAGRAM_REDIRECT_URI, 'code': code}
                response = await client.post(short_lived_token_url, data=short_lived_payload)
                response.raise_for_status()
                short_lived_token_data = response.json()
                long_lived_token_url = 'https://graph.instagram.com/access_token'
                params = {'grant_type': 'ig_exchange_token', 'client_secret': self.INSTAGRAM_CLIENT_SECRET, 'access_token': short_lived_token_data['access_token']}
                response = await client.get(long_lived_token_url, params=params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                print(f'Error exchanging Instagram code: {e.response.text}')
                raise HTTPException(status_code=400, detail=f'Failed to exchange code for token: {e.response.text}')
            except Exception as e:
                print(f'An unexpected error occurred: {e}')
                raise HTTPException(status_code=500, detail='An unexpected error occurred during Instagram authentication.')

    async def get_instagram_user_profile(self, access_token: str) -> dict:
        """Récupère le profil utilisateur d'Instagram en utilisant le token d'accès."""
        profile_url = f'https://graph.instagram.com/v23.0/me?fields=id,username&access_token={access_token}'
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(profile_url)
                response.raise_for_status()
                print(f"🔍 DEBUG get_instagram_user_profile - response: {response.json()}")
                return response.json()
            except httpx.HTTPStatusError as e:
                print(f'Error fetching Instagram profile: {e.response.text}')
                raise HTTPException(status_code=400, detail=f'Failed to fetch Instagram profile: {e.response.text}')
            except Exception as e:
                print(f'An unexpected error occurred while fetching profile: {e}')
                raise HTTPException(status_code=500, detail='An unexpected error occurred while fetching Instagram profile.')

    async def get_instagram_business_account(self, access_token: str) -> dict:
        """Récupère l'ID et le nom d'utilisateur du compte Instagram Business via l'API Graph d'Instagram."""
        url = 'https://graph.instagram.com/v23.0/me?fields=id,user_id,username,account_type,profile_picture_url'
        headers = {'Authorization': f'Bearer {access_token}'}
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                print(f"🔍 DEBUG get_instagram_business_account - response: {response.json()}")
                data = response.json()
                if data.get('account_type') not in ['BUSINESS', 'CREATOR']:
                    raise HTTPException(status_code=400, detail='The authenticated account is not an Instagram Business or Creator account.')
                # Utiliser user_id (IG ID) au lieu de id (app-scoped ID) pour correspondre aux webhooks
                ig_id = data.get('user_id', data.get('id'))  # Fallback vers id si user_id n'est pas disponible
                return {'id': ig_id, 'username': data['username'], 'profile_picture_url': data.get('profile_picture_url')}
            except httpx.HTTPStatusError as e:
                print(f'Error fetching Instagram Business Account: {e.response.text}')
                raise HTTPException(status_code=400, detail=f'Failed to fetch Instagram Business Account: {e.response.text}')
            except Exception as e:
                print(f'An unexpected error occurred: {e}')
                raise HTTPException(status_code=500, detail='An unexpected error occurred while fetching Instagram Business Account.')

    

social_auth_service = SocialAuthService()