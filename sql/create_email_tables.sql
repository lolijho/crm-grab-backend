-- Tabella per la cronologia delle email inviate
CREATE TABLE IF NOT EXISTS email_history (
  id SERIAL PRIMARY KEY,
  contact_id INTEGER REFERENCES contacts(id) ON DELETE CASCADE,
  to_email VARCHAR(255) NOT NULL,
  subject TEXT NOT NULL,
  content TEXT NOT NULL,
  sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabella per i template email personalizzati
CREATE TABLE IF NOT EXISTS email_templates (
  id SERIAL PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,
  subject TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indici per migliorare le performance
CREATE INDEX IF NOT EXISTS idx_email_history_contact_id ON email_history(contact_id);
CREATE INDEX IF NOT EXISTS idx_email_history_sent_at ON email_history(sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_templates_user_id ON email_templates(user_id);
CREATE INDEX IF NOT EXISTS idx_email_templates_name ON email_templates(name);

-- RLS (Row Level Security) per i template email
ALTER TABLE email_templates ENABLE ROW LEVEL SECURITY;

-- Policy per permettere ai utenti di vedere solo i propri template
CREATE POLICY "Users can view own email templates" ON email_templates
  FOR SELECT USING (auth.uid() = user_id);

-- Policy per permettere ai utenti di inserire i propri template
CREATE POLICY "Users can insert own email templates" ON email_templates
  FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Policy per permettere ai utenti di aggiornare i propri template
CREATE POLICY "Users can update own email templates" ON email_templates
  FOR UPDATE USING (auth.uid() = user_id);

-- Policy per permettere ai utenti di eliminare i propri template
CREATE POLICY "Users can delete own email templates" ON email_templates
  FOR DELETE USING (auth.uid() = user_id);

-- RLS per la cronologia email
ALTER TABLE email_history ENABLE ROW LEVEL SECURITY;

-- Policy per permettere ai utenti di vedere la cronologia dei propri contatti
CREATE POLICY "Users can view email history for own contacts" ON email_history
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM contacts 
      WHERE contacts.id = email_history.contact_id 
      AND contacts.user_id = auth.uid()
    )
  );

-- Policy per permettere ai utenti di inserire cronologia per i propri contatti
CREATE POLICY "Users can insert email history for own contacts" ON email_history
  FOR INSERT WITH CHECK (
    EXISTS (
      SELECT 1 FROM contacts 
      WHERE contacts.id = email_history.contact_id 
      AND contacts.user_id = auth.uid()
    )
  );

-- Trigger per aggiornare automatically updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger per email_history
CREATE TRIGGER update_email_history_updated_at BEFORE UPDATE ON email_history
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Trigger per email_templates  
CREATE TRIGGER update_email_templates_updated_at BEFORE UPDATE ON email_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); 