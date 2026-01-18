#!/usr/bin/env python3
"""Test-Script für HayMAS"""

import os
import glob
from dotenv import load_dotenv
load_dotenv()

from agents import OrchestratorAgent, ResearcherAgent, StructurerAgent

# Output-Ordner aufräumen
output_dir = os.path.join(os.path.dirname(__file__), "output")
for f in glob.glob(os.path.join(output_dir, "*.md")):
    os.remove(f)
for f in glob.glob(os.path.join(output_dir, "*.pptx")):
    os.remove(f)

print('Initialisiere Agenten...')
orchestrator = OrchestratorAgent()
researcher = ResearcherAgent()
structurer = StructurerAgent()
orchestrator.set_agents(researcher, structurer)

print('\nStarte Präsentationserstellung...')
question = 'Was ist RAG (Retrieval Augmented Generation)?'

result = None
for i, event in enumerate(orchestrator.process_presentation(question)):
    agent_short = event.agent_name[:15]
    content_short = event.content[:120].replace('\n', ' ')
    print(f'[{i:02d}] {agent_short:15s} | {event.event_type.value:12s} | {content_short}')
    
    if event.event_type.value == 'response' and event.data:
        result = event.data
    
    if i > 50:
        print('\n... (abgebrochen)')
        break

print()
if result:
    print(f'✅ FERTIG! PPT erstellt: {result.get("ppt_path", "?")}')
else:
    print('❌ Kein Ergebnis')
