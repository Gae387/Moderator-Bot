import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient();

function StatusPage() {
  const commands = [
    { name: '.ban', desc: 'Banna un membro' },
    { name: '.kick', desc: 'Espelle un membro' },
    { name: '.mute', desc: 'Silenzia un membro' },
    { name: '.unmute', desc: 'De-silenzia un membro' },
    { name: '.warn', desc: 'Avverte un membro' },
    { name: '.pex', desc: 'Assegna un ruolo' },
    { name: '.depex', desc: 'Rimuove un ruolo' },
    { name: '.clear', desc: 'Elimina messaggi' },
    { name: '.lock', desc: 'Blocca un canale' },
    { name: '.unlock', desc: 'Sblocca un canale' },
    { name: '.say', desc: 'Invia un messaggio come bot' },
    { name: '.embed', desc: 'Invia un embed personalizzato' },
    { name: '.setwelcome', desc: 'Imposta messaggio di benvenuto' },
    { name: '.setgoodbye', desc: 'Imposta messaggio di addio' },
  ];

  return (
    <div style={{ minHeight: '100vh', background: '#23272a', color: '#fff', fontFamily: 'sans-serif' }}>
      {/* Header */}
      <div style={{ background: '#2c2f33', padding: '32px 0', textAlign: 'center', borderBottom: '3px solid #7289da' }}>
        <div style={{ fontSize: 56 }}>🛡️</div>
        <h1 style={{ margin: '12px 0 4px', fontSize: 32, color: '#7289da' }}>Moderator Bot</h1>
        <p style={{ margin: 0, color: '#99aab5', fontSize: 16 }}>Bot di moderazione per Discord</p>
        <div style={{ marginTop: 16, display: 'inline-flex', alignItems: 'center', gap: 8,
          background: '#1e2124', padding: '8px 20px', borderRadius: 20 }}>
          <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#43b581',
            boxShadow: '0 0 8px #43b581' }} />
          <span style={{ color: '#43b581', fontWeight: 600 }}>Online</span>
        </div>
      </div>

      {/* Info */}
      <div style={{ maxWidth: 700, margin: '0 auto', padding: '32px 16px' }}>
        <div style={{ display: 'flex', gap: 16, marginBottom: 32, flexWrap: 'wrap' }}>
          {[
            { label: 'Prefisso', value: '.' },
            { label: 'Comandi', value: String(commands.length) },
            { label: 'Linguaggio', value: 'Italiano' },
          ].map(({ label, value }) => (
            <div key={label} style={{ flex: 1, minWidth: 140, background: '#2c2f33',
              borderRadius: 12, padding: '20px 24px', textAlign: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#7289da' }}>{value}</div>
              <div style={{ color: '#99aab5', fontSize: 13, marginTop: 4 }}>{label}</div>
            </div>
          ))}
        </div>

        {/* Commands */}
        <h2 style={{ color: '#7289da', marginBottom: 16, fontSize: 18 }}>📋 Comandi disponibili</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 10 }}>
          {commands.map(({ name, desc }) => (
            <div key={name} style={{ background: '#2c2f33', borderRadius: 8, padding: '12px 16px',
              display: 'flex', alignItems: 'center', gap: 12 }}>
              <code style={{ background: '#23272a', color: '#7289da', padding: '2px 8px',
                borderRadius: 4, fontSize: 13, fontWeight: 700, whiteSpace: 'nowrap' }}>{name}</code>
              <span style={{ color: '#99aab5', fontSize: 13 }}>{desc}</span>
            </div>
          ))}
        </div>

        <p style={{ textAlign: 'center', color: '#4f545c', marginTop: 40, fontSize: 13 }}>
          Usa <code style={{ color: '#7289da' }}>.help</code> nel tuo server per tutti i dettagli
        </p>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <StatusPage />
    </QueryClientProvider>
  );
}
