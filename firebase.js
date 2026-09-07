import { initializeApp } from "https://www.gstatic.com/firebasejs/12.18.0/firebase-app.js";
import { getAuth } from "https://www.gstatic.com/firebasejs/12.18.0/firebase-auth.js";
import { getFirestore } from "https://www.gstatic.com/firebasejs/12.18.0/firebase-firestore.js";
const firebaseConfig={apiKey:"AIzaSyCI6eBN_BOMQjX8p0lcNYBdjl8a7hKW1sY",authDomain:"ganapati-eye-clinic.firebaseapp.com",projectId:"ganapati-eye-clinic",storageBucket:"ganapati-eye-clinic.firebasestorage.app",messagingSenderId:"801510803706",appId:"1:801510803706:web:f36b7d4948d409cd4a2143",measurementId:"G-945VZHYVHR"};
const app=initializeApp(firebaseConfig),auth=getAuth(app),db=getFirestore(app); export {app,auth,db};
