export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });
  const { message, phoneNumbers } = req.body || {};
  if (!message || !Array.isArray(phoneNumbers) || !phoneNumbers.length) {
    return res.status(400).json({ error: 'Message and at least one phone number are required.' });
  }
  const numbers = [...new Set(phoneNumbers.map(v => String(v || '').trim()).filter(Boolean))];
  const url = process.env.SMS_GATE_URL || 'https://api.sms-gate.app/3rdparty/v1/messages';
  const username = process.env.SMS_GATE_USERNAME;
  const password = process.env.SMS_GATE_PASSWORD;
  const deviceId = process.env.SMS_GATE_DEVICE_ID;
  const simNumber = Number(process.env.SMS_GATE_SIM_NUMBER || 1);
  if (!username || !password || !deviceId) {
    return res.status(503).json({ error: 'SMS gateway is not configured. Add SMS_GATE_USERNAME, SMS_GATE_PASSWORD and SMS_GATE_DEVICE_ID in Vercel environment variables.' });
  }
  try {
    const auth = Buffer.from(`${username}:${password}`).toString('base64');
    const response = await fetch(`${url}?skipPhoneValidation=true&deviceActiveWithin=12`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Basic ${auth}` },
      body: JSON.stringify({ textMessage: { text: message }, deviceId, phoneNumbers: numbers, simNumber, ttl: 3600, priority: 100 })
    });
    const text = await response.text();
    let data; try { data = JSON.parse(text); } catch { data = { raw: text }; }
    if (!response.ok) return res.status(response.status).json({ error: data?.message || data?.error || 'SMS gateway rejected the request.', details: data });
    return res.status(200).json({ ok: true, message: `SMS request accepted for ${numbers.length} recipient${numbers.length === 1 ? '' : 's'}.`, gateway: data });
  } catch (e) {
    console.error(e);
    return res.status(502).json({ error: 'Could not connect to the SMS gateway.' });
  }
}
