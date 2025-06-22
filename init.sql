-- Testing Creation of Knowledge Base only if not exists
CREATE KNOWLEDGE_BASE IF NOT EXISTS military_kb USING
  embedding_model = {
    "provider": "ollama",
    "model_name": "nomic-embed-text",
    "base_url": "http://ollama:11434"
  },
  metadata_columns = ['country', 'branch', 'category'],
  content_columns = ['strategy_text'],
  id_column = 'doc_id';

--Testing of Insertion sample data into KB
INSERT INTO military_kb (doc_id, country, branch, category, strategy_text)
VALUES 
  ('R001', 'Russia', 'Army', 'Hybrid Warfare', 'Hybrid warfare combines conventional and unconventional tactics including cyber attacks and disinformation campaigns.'),
  ('I001', 'India', 'Navy', 'Naval Doctrine', 'India''s naval doctrine emphasizes maritime security and regional dominance in the Indian Ocean.'),
  ('C001', 'China', 'Air Force', 'Air Superiority', 'China''s air force focuses on securing airspace and enhancing long-range strike capabilities.');
