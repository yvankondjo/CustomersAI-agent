"""
Test rapide du RAG Agent
"""

import asyncio
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.rag_agent import create_rag_agent
from app.core.constants import DEFAULT_USER_ID


async def quick_test():
    """Test rapide"""
    print("🚀 Test rapide du RAG Agent\n")
    
    conversation_id = f"quick_test_{datetime.now().timestamp()}"
    
    print(f"📝 Création de l'agent...")
    agent = create_rag_agent(
        user_id=DEFAULT_USER_ID,
        conversation_id=conversation_id,
        test_mode=False,
        checkpointer=None
    )
    print("✅ Agent créé\n")
    
    test_questions = [
        "Bonjour, comment allez-vous ?",
        "Quels sont vos horaires ?",
        "Je veux réserver un rendez-vous"
    ]
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n{'='*60}")
        print(f"Question {i}: {question}")
        print('='*60)
        
        try:
            result = await agent.process_message(question)
            print(f"\nRéponse: {result['response']}")
            print(f"Sources: {len(result.get('sources', []))}")
            print(f"Escalation: {result.get('escalated', False)}")
        except Exception as e:
            print(f"❌ Erreur: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(quick_test())

