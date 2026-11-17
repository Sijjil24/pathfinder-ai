import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";
import { getAuth, GoogleAuthProvider, signInWithPopup, signInWithEmailAndPassword,
  createUserWithEmailAndPassword, updateProfile, sendPasswordResetEmail } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";

const nextUrl = new URLSearchParams(location.search).get('next') || '';
const box = document.getElementById('auth-msg');
const say = (t, type = 'error') => {
  if (!box) return;
  box.textContent = t;
  box.className = 'auth-msg show ' + type;
};
const friendly = {
  'auth/invalid-credential': 'Wrong email or password.', 'auth/wrong-password': 'Wrong email or password.',
  'auth/user-not-found': 'No account with that email.', 'auth/email-already-in-use': 'That email already has an account.',
  'auth/weak-password': 'Password must be at least 6 characters.', 'auth/invalid-email': 'That email looks wrong.',
  'auth/popup-closed-by-user': 'Google window was closed.', 'auth/too-many-requests': 'Too many tries. Wait a minute.',
  'auth/unauthorized-domain': 'Open the site at http://localhost:5000 (domain not authorised in Firebase).',
  'auth/configuration-not-found': 'Firebase is not configured for this app.',
};
const fail = e => {
  const code = e && e.code ? e.code : null;
  const message = code && friendly[code] ? friendly[code] : (e && e.message) || 'Something went wrong.';
  say(message);
};

const firebaseConfig = window.FIREBASE_CONFIG || {};
const hasFirebaseConfig = !!(firebaseConfig.apiKey && firebaseConfig.authDomain && firebaseConfig.projectId && firebaseConfig.appId);

if (!hasFirebaseConfig) {
  const googleBtn = document.getElementById('google-btn');
  if (googleBtn) {
    googleBtn.disabled = true;
    googleBtn.title = 'Firebase is not configured';
  }
  say('Firebase is not configured. Set the env vars and refresh the page.', 'error');
} else {
  const auth = getAuth(initializeApp(firebaseConfig));

  async function finish(user) {
    const idToken = await user.getIdToken();
    const r = await fetch('/auth/firebase', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ idToken, name: user.displayName || '', next: nextUrl }),
    });
    let d = {};
    try { d = await r.json(); } catch (error) { /* ignore invalid JSON */ }
    if (!r.ok) throw new Error(d.error || 'Sign-in failed.');
    location.href = d.next || '/dashboard';
  }

  document.getElementById('google-btn')?.addEventListener('click', async () => {
    try { const c = await signInWithPopup(auth, new GoogleAuthProvider()); await finish(c.user); } catch (e) { fail(e); }
  });

  document.querySelectorAll('form[data-auth]').forEach(form => form.addEventListener('submit', async ev => {
    ev.preventDefault();
    const kind = form.dataset.auth, f = new FormData(form), email = (f.get('email') || '').trim(), pw = f.get('password');
    const btn = form.querySelector('button[type=submit]');
    if (!btn) return;
    btn.disabled = true;
    try {
      if (kind === 'login') await finish((await signInWithEmailAndPassword(auth, email, pw)).user);
      else if (kind === 'signup') {
        const c = await createUserWithEmailAndPassword(auth, email, pw);
        await updateProfile(c.user, { displayName: (f.get('name') || '').trim() });
        await finish(c.user);
      } else if (kind === 'forgot') {
        await sendPasswordResetEmail(auth, email);
        say('Reset link sent! Check your inbox (and spam folder).', 'success');
      }
    } catch (e) { fail(e); }
    btn.disabled = false;
  }));
}
