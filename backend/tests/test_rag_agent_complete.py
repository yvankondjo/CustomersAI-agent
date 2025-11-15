"""
Tests complets pour le RAG Agent
Teste FAQ, recherche, réservation, et escalation
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.rag_agent import create_rag_agent
from app.core.constants import DEFAULT_USER_ID
from app.db.session import get_db


async def test_faq_priority():
    """Test que la FAQ est utilisée en priorité avant le search tool"""
    print("\n" + "="*60)
    print("TEST 1: FAQ Priority")
    print("="*60)
    
    conversation_id = f"test_faq_{datetime.now().timestamp()}"
    
    agent = create_rag_agent(
        user_id=DEFAULT_USER_ID,
        conversation_id=conversation_id,
        test_mode=False,
        checkpointer=None
    )
    
    question = "Quels sont vos horaires d'ouverture ?"
    print(f"\nQuestion: {question}")
    
    result = await agent.process_message(question)
    
    print(f"\nRéponse: {result['response']}")
    print(f"Sources utilisées: {len(result.get('sources', []))}")
    print(f"Escalation: {result.get('escalated', False)}")
    
    if len(result.get('sources', [])) == 0:
        print("✅ SUCCESS: FAQ utilisée directement (pas de search tool)")
    else:
        print("⚠️ WARNING: Search tool utilisé alors que la FAQ devrait suffire")
    
    return result


async def test_search_tool():
    """Test que le search tool fonctionne correctement"""
    print("\n" + "="*60)
    print("TEST 2: Search Tool")
    print("="*60)
    
    conversation_id = f"test_search_{datetime.now().timestamp()}"
    
    agent = create_rag_agent(
        user_id=DEFAULT_USER_ID,
        conversation_id=conversation_id,
        test_mode=False,
        checkpointer=None
    )
    
    question = "Quelles sont les informations sur vos produits ?"
    print(f"\nQuestion: {question}")
    
    result = await agent.process_message(question)
    
    print(f"\nRéponse: {result['response']}")
    print(f"Sources trouvées: {len(result.get('sources', []))}")
    
    if len(result.get('sources', [])) > 0:
        print("✅ SUCCESS: Search tool a trouvé des résultats")
        for i, source in enumerate(result['sources'][:3], 1):
            print(f"  Source {i}: {source[:100]}...")
    else:
        print("⚠️ WARNING: Aucune source trouvée (peut être normal si pas de documents)")
    
    return result


async def test_check_availability():
    """Test de vérification de disponibilité"""
    print("\n" + "="*60)
    print("TEST 3: Check Availability")
    print("="*60)
    
    conversation_id = f"test_availability_{datetime.now().timestamp()}"
    
    agent = create_rag_agent(
        user_id=DEFAULT_USER_ID,
        conversation_id=conversation_id,
        test_mode=False,
        checkpointer=None
    )
    
    question = "Je veux réserver un rendez-vous demain"
    print(f"\nQuestion: {question}")
    
    result = await agent.process_message(question)
    
    print(f"\nRéponse: {result['response']}")
    
    if "disponible" in result['response'].lower() or "available" in result['response'].lower() or "créneau" in result['response'].lower():
        print("✅ SUCCESS: L'agent a vérifié la disponibilité")
    elif "cal.com" in result['response'].lower() or "configuré" in result['response'].lower():
        print("ℹ️ INFO: Cal.com n'est pas configuré (normal si pas de clé API)")
    else:
        print("⚠️ WARNING: Réponse inattendue")
    
    return result


async def test_escalation():
    """Test d'escalation pour situation complexe"""
    print("\n" + "="*60)
    print("TEST 4: Escalation")
    print("="*60)
    
    conversation_id = f"test_escalation_{datetime.now().timestamp()}"
    
    agent = create_rag_agent(
        user_id=DEFAULT_USER_ID,
        conversation_id=conversation_id,
        test_mode=False,
        checkpointer=None
    )
    
    question = "Je veux un remboursement complet immédiatement, c'est inadmissible !"
    print(f"\nQuestion: {question}")
    
    result = await agent.process_message(question)
    
    print(f"\nRéponse: {result['response']}")
    print(f"Escalation: {result.get('escalated', False)}")
    
    if result.get('escalated', False):
        print("✅ SUCCESS: Conversation escaladée correctement")
    elif "humain" in result['response'].lower() or "équipe" in result['response'].lower() or "support" in result['response'].lower():
        print("✅ SUCCESS: L'agent propose l'escalation")
    else:
        print("⚠️ WARNING: L'escalation n'a pas été déclenchée")
    
    return result


async def test_booking_flow():
    """Test du flux complet de réservation"""
    print("\n" + "="*60)
    print("TEST 5: Booking Flow")
    print("="*60)
    
    conversation_id = f"test_booking_{datetime.now().timestamp()}"
    
    agent = create_rag_agent(
        user_id=DEFAULT_USER_ID,
        conversation_id=conversation_id,
        test_mode=False,
        checkpointer=None
    )
    
    messages = [
        "Je veux réserver un rendez-vous",
        "Mon nom est Jean Dupont et mon email est jean.dupont@example.com",
        "Je veux un rendez-vous demain à 14h"
    ]
    
    for i, message in enumerate(messages, 1):
        print(f"\n--- Message {i} ---")
        print(f"Client: {message}")
        
        result = await agent.process_message(message)
        
        print(f"Agent: {result['response']}")
        
        if i == len(messages):
            if "réservé" in result['response'].lower() or "booked" in result['response'].lower() or "confirmé" in result['response'].lower():
                print("✅ SUCCESS: Réservation créée")
            elif "disponible" in result['response'].lower() or "available" in result['response'].lower():
                print("ℹ️ INFO: L'agent vérifie la disponibilité (bon comportement)")
            else:
                print("⚠️ WARNING: Réponse inattendue")
    
    return result


async def run_all_tests():
    """Exécute tous les tests"""
    print("\n" + "="*60)
    print("TESTS COMPLETS DU RAG AGENT")
    print("="*60)
    
    results = {}
    
    try:
        results['faq'] = await test_faq_priority()
    except Exception as e:
        print(f"❌ ERREUR dans test_faq_priority: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        results['search'] = await test_search_tool()
    except Exception as e:
        print(f"❌ ERREUR dans test_search_tool: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        results['availability'] = await test_check_availability()
    except Exception as e:
        print(f"❌ ERREUR dans test_check_availability: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        results['escalation'] = await test_escalation()
    except Exception as e:
        print(f"❌ ERREUR dans test_escalation: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        results['booking'] = await test_booking_flow()
    except Exception as e:
        print(f"❌ ERREUR dans test_booking_flow: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("RÉSUMÉ DES TESTS")
    print("="*60)
    
    for test_name, result in results.items():
        if result:
            print(f"\n{test_name.upper()}:")
            print(f"  - Réponse générée: {'✅' if result.get('response') else '❌'}")
            print(f"  - Sources: {len(result.get('sources', []))}")
            print(f"  - Escalation: {'✅' if result.get('escalated') else '❌'}")


if __name__ == "__main__":
    asyncio.run(run_all_tests())

