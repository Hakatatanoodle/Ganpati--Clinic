import {auth,db} from "./firebase.js";import{createUserWithEmailAndPassword,signInWithEmailAndPassword,onAuthStateChanged,signOut}from"https://www.gstatic.com/firebasejs/12.18.0/firebase-auth.js";import{collection,addDoc,updateDoc,deleteDoc,doc,onSnapshot,query,orderBy,serverTimestamp}from"https://www.gstatic.com/firebasejs/12.18.0/firebase-firestore.js";
const $=id=>document.getElementById(id);
const PROFILE_PREFIX="ganapati_profile_";
let activeUserUid="";
function applyTheme(on){document.body.classList.toggle("dark-theme",!!on);const t=$("darkThemeToggle");if(t)t.checked=!!on}
function profileKey(uid){return PROFILE_PREFIX+uid}
function loadProfileSettings(uid,email=""){activeUserUid=uid;let data={};try{data=JSON.parse(localStorage.getItem(profileKey(uid))||"{}")}catch{};const name=data.name||"";$("profileName").value=name;$("profileStatus").textContent="";const photo=data.photo||"";const img=$("profilePhoto"),initials=$("profileInitials");if(photo){img.src=photo;img.classList.add("has-photo");initials.classList.add("hide")}else{img.removeAttribute("src");img.classList.remove("has-photo");initials.textContent=(name||email||"U").trim().charAt(0).toUpperCase()||"U";initials.classList.remove("hide")}applyTheme(data.dark===true)}
function saveProfileSettings(){if(!activeUserUid)return;const name=$("profileName").value.trim();let data={name};try{data=Object.assign(JSON.parse(localStorage.getItem(profileKey(activeUserUid))||"{}"),data);localStorage.setItem(profileKey(activeUserUid),JSON.stringify(data));$("profileStatus").textContent="Profile saved.";setTimeout(()=>$("profileStatus").textContent="",1800);const email=$("userEmail").textContent||"";$("profileInitials").textContent=(name||email||"U").charAt(0).toUpperCase()}catch{$("profileStatus").textContent="Could not save profile on this device."}}
function saveThemeSetting(on){if(!activeUserUid)return;let data={};try{data=JSON.parse(localStorage.getItem(profileKey(activeUserUid))||"{}")}catch{};data.dark=!!on;try{localStorage.setItem(profileKey(activeUserUid),JSON.stringify(data))}catch{};applyTheme(on)}
applyTheme(false);
const ids=["name","ageYears","ageMonths","ageDays","age","patientDate","contact","address","gender","occupation","presentingComplaint","ucvaRe","ucvaLe","phRe","phLe","dryRe","dryLe","wetRe","wetLe","bcvaReSph","bcvaReCyl","bcvaReAxis","bcvaReVa","bcvaLeSph","bcvaLeCyl","bcvaLeAxis","bcvaLeVa","bcvaAddRe","bcvaAddLe","bcvaPd","pgReSph","pgReCyl","pgReAxis","pgReVa","pgLeSph","pgLeCyl","pgLeAxis","pgLeVa","pgAddRe","pgAddLe","systemicDetails","ocularHistory","sch1Re","sch1Le","sch2Re","sch2Le","bp","colorVisionRe","colorVisionLe","iopRe","iopLe","examiner","diagnosis","diagnosisFinal","additionalNotes","medicines","suggestions","lensLeSph","lensLeCyl","lensLeAxis","lensLeVa","lensLeAdd","lensReSph","lensReCyl","lensReAxis","lensReVa","lensReAdd","lensType","lensRemarks","frameType","lensMaterial","lensCoating","lensCoatingOther","frameAmount","lensAmount","totalAmount","advanceAmount","remainingAmount","medicinesAmount","clinicalTestAmount","othersAmount"];let records=[],unsub=null;
function today(){let d=new Date();return d.toISOString().slice(0,10)}$("patientDate").value=today();
function syncAge(){const y=$("ageYears").value.trim(),m=$("ageMonths").value.trim(),d=$("ageDays").value.trim();$("age").value=(y||"0")+" Years, "+(m||"0")+" Months, "+(d||"0")+" Days"}
$("ageYears").addEventListener("input",syncAge);$("ageMonths").addEventListener("input",syncAge);$("ageDays").addEventListener("input",syncAge);
function calculateTotal(){const frame=Number($("frameAmount").value)||0;const lens=Number($("lensAmount").value)||0;const medicines=Number($("medicinesAmount").value)||0;const clinical=Number($("clinicalTestAmount").value)||0;const others=Number($("othersAmount").value)||0;const advance=Number($("advanceAmount").value)||0;const total=frame+lens+medicines+clinical+others;$("totalAmount").value=total.toFixed(2);$("remainingAmount").value=(total-advance).toFixed(2)}
$("frameAmount").addEventListener("input",calculateTotal);$("lensAmount").addEventListener("input",calculateTotal);$("medicinesAmount").addEventListener("input",calculateTotal);$("clinicalTestAmount").addEventListener("input",calculateTotal);$("othersAmount").addEventListener("input",calculateTotal);$("advanceAmount").addEventListener("input",calculateTotal);
function toggleLensCoatingOther(){const show=$("lensCoating").value==="others";$("lensCoatingOtherWrap").classList.toggle("hide",!show);if(!show)$("lensCoatingOther").value=""}
$("lensCoating").addEventListener("change",toggleLensCoatingOther);toggleLensCoatingOther();
$("toSignup").onclick=()=>{$("loginPanel").classList.add("hide");$("signupPanel").classList.remove("hide")};$("toLogin").onclick=()=>{$("signupPanel").classList.add("hide");$("loginPanel").classList.remove("hide")};
$("loginForm").onsubmit=async e=>{e.preventDefault();try{await signInWithEmailAndPassword(auth,$("loginEmail").value.trim(),$("loginPassword").value)}catch(x){$("loginError").textContent=err(x)}};$("signupForm").onsubmit=async e=>{e.preventDefault();$("signupError").textContent="";if($("signupPassword").value!==$("signupConfirm").value){$("signupError").textContent="Passwords do not match.";return}try{await createUserWithEmailAndPassword(auth,$("signupEmail").value.trim(),$("signupPassword").value)}catch(x){$("signupError").textContent=err(x)}};function err(x){if(x.code?.includes("email-already"))return"This email already has an account.";if(x.code?.includes("weak-password"))return"Password must be at least 6 characters.";if(x.code?.includes("invalid-credential"))return"Incorrect email or password.";return"Authentication failed. Check Firebase Authentication."}
const logoutModal=$("logoutModal");function openLogout(){logoutModal.classList.remove("hide");setTimeout(()=>$("logoutNo").focus(),0)}function closeLogout(){logoutModal.classList.add("hide")}$("logout").onclick=openLogout;$("sideLogout").onclick=openLogout;$("logoutNo").onclick=closeLogout;$("logoutYes").onclick=async()=>{closeLogout();await signOut(auth)};logoutModal.addEventListener("click",e=>{if(e.target===logoutModal)closeLogout()});document.addEventListener("keydown",e=>{if(e.key==="Escape"&&!logoutModal.classList.contains("hide"))closeLogout();if(e.key==="ArrowLeft"&&!$("formCard").classList.contains("hide")){const fields=getFieldOrder();const active=document.activeElement;const index=fields.indexOf(active);if(index>0){e.preventDefault();fields[index-1].focus();fields[index-1].scrollIntoView({behavior:"smooth",block:"center"})}else if(index===0){e.preventDefault();window.scrollTo({top:0,behavior:"smooth"})}}});$("clear").onclick=reset;$("saveTop").onclick=()=>$("patientForm").requestSubmit();$("cancel").onclick=reset;$("search").oninput=render;
function showSection(id){const sections=["dashboardCard","formCard","recordsCard","reportsCard","settingsCard","smsBroadcastCard","usersCard","backupCard","aboutCard"];sections.forEach(x=>$(x).classList.toggle("hide",x!==id));$("formActions").classList.toggle("hide",id!=="formCard");const navs=[...document.querySelectorAll(".nav[data-target]")];const activeNav=id==="formCard"?navs.find(b=>b.dataset.target==="formCard"):navs.find(b=>b.dataset.target===id);navs.forEach(b=>b.classList.toggle("active",b===activeNav));if(id==="recordsCard")render();const titles={dashboardCard:"Dashboard",formCard:"Add / Edit Patient Record",recordsCard:"Patient Records",reportsCard:"Reports",settingsCard:"Settings",smsBroadcastCard:"SMS Broadcast",usersCard:"Users",backupCard:"Backup",aboutCard:"About Us"};$("pageTitle").textContent=titles[id]||"Dashboard";$("breadcrumb").textContent=id==="dashboardCard"?"Dashboard":`Dashboard › ${titles[id]||""}`;window.scrollTo({top:0,behavior:"smooth"})}

const emojiList=["😊","🙂","😂","😍","🙏","❤️","👋","👍","🎉","✨","👓","👁️","🏥","📅","💙","🌟","✅","⚕️","📞","🩺","🎁","🙂","😃","😄","😉","😎"];
function normalizePhone(v){let x=String(v||"").replace(/[^\d+]/g,"");if(x.startsWith("00"))x="+"+x.slice(2);if(x.startsWith("98")||x.startsWith("97"))x="+977"+x;return x}
function smsRecipients(){const q=($('smsPatientSearch')?.value||"").toLowerCase().trim();return records.filter(r=>{const name=String(r.name||"").toLowerCase(),phone=String(r.contact||"").toLowerCase();return !q||name.includes(q)||phone.includes(q)})}
function renderSmsPatients(){const box=$("smsPatients");if(!box)return;const selected=new Set([...box.querySelectorAll('input[type="checkbox"]:checked')].map(x=>x.value));const list=smsRecipients();box.innerHTML=list.length?list.map(r=>{const phone=normalizePhone(r.contact);const disabled=!phone||phone.length<10;return `<label class="sms-patient"><input type="checkbox" class="patient-check" value="${esc(r.id)}" data-phone="${esc(phone)}" ${selected.has(r.id)?"checked":""} ${disabled?"disabled":""}><span><b>${esc(r.name||"Unnamed")}</b><small>${esc(r.contact||"No phone")}${disabled?" · Invalid phone":""}</small></span></label>`}).join(""):'<div class="empty">No patients found.</div>';updateSmsSelectionCount();syncSelectAll()}
function updateSmsSelectionCount(){const n=document.querySelectorAll('#smsPatients .patient-check:checked').length;$("selectedPatientCount").textContent=`${n} selected`}
function syncSelectAll(){const checks=[...document.querySelectorAll('#smsPatients .patient-check:not(:disabled)')],selected=checks.filter(x=>x.checked);const all=$('selectAllPatients');if(!all)return;all.checked=checks.length>0&&selected.length===checks.length;all.indeterminate=selected.length>0&&selected.length<checks.length}
function selectedSmsRecipients(){return [...document.querySelectorAll('#smsPatients .patient-check:checked')].map(x=>x.dataset.phone).filter(Boolean)}
function updateSmsCount(){const ta=$('smsMessage');if(!ta)return;if(ta.value.length>1000)ta.value=ta.value.slice(0,1000);$("smsCount").textContent=`${ta.value.length} / 1000 letters`}
function initSmsBroadcast(){if(!$('smsMessage'))return;emojiList.forEach(e=>{const b=document.createElement('button');b.type='button';b.textContent=e;b.className='emoji-choice';b.onclick=()=>{const ta=$('smsMessage'),start=ta.selectionStart,end=ta.selectionEnd;ta.value=ta.value.slice(0,start)+e+ta.value.slice(end);ta.focus();ta.selectionStart=ta.selectionEnd=start+e.length;updateSmsCount()};$('emojiPicker').appendChild(b)});$('emojiToggle').onclick=()=>$('emojiPicker').classList.toggle('hide');$('smsMessage').addEventListener('input',updateSmsCount);$('smsPatientSearch').addEventListener('input',renderSmsPatients);$('smsPatients').addEventListener('change',()=>{updateSmsSelectionCount();syncSelectAll()});$('selectAllPatients').addEventListener('change',e=>{document.querySelectorAll('#smsPatients .patient-check:not(:disabled)').forEach(c=>c.checked=e.target.checked);updateSmsSelectionCount();syncSelectAll()});$('sendBroadcast').onclick=sendSmsBroadcast;updateSmsCount();renderSmsPatients()}
async function sendSmsBroadcast(){const message=$('smsMessage').value.trim();const recipients=selectedSmsRecipients();if(!message){$('smsStatus').textContent='Please type a message.';$('smsStatus').className='error';return}if(!recipients.length){$('smsStatus').textContent='Please select at least one patient.';$('smsStatus').className='error';return}if(!confirm(`Send this SMS to ${recipients.length} patient${recipients.length===1?'':'s'}?`))return;$('sendBroadcast').disabled=true;$('smsStatus').textContent=`Sending to ${recipients.length} patient${recipients.length===1?'':'s'}...`;$('smsStatus').className='';try{const res=await fetch('/api/send-sms',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message,phoneNumbers:recipients})});const data=await res.json().catch(()=>({}));if(!res.ok)throw new Error(data.error||'SMS gateway could not send the messages.');$('smsStatus').textContent=data.message||`SMS request accepted for ${recipients.length} recipient${recipients.length===1?'':'s'}.`;$('smsStatus').className='success';$('smsMessage').value='';updateSmsCount();document.querySelectorAll('#smsPatients .patient-check').forEach(c=>c.checked=false);updateSmsSelectionCount();syncSelectAll()}catch(e){console.error(e);$('smsStatus').textContent=e.message||'SMS sending failed.';$('smsStatus').className='error'}finally{$('sendBroadcast').disabled=false}}
function getFieldOrder(){return [...patientForm.querySelectorAll("input:not([type=hidden]):not([readonly]):not([disabled]), select:not([disabled]), textarea:not([disabled])")]}
const formSectionTitles=[...patientForm.querySelectorAll(".title")];
function goPreviousSection(){if($("formCard").classList.contains("hide"))return;const active=document.activeElement;let currentIndex=-1;if(active&&patientForm.contains(active)){const y=active.getBoundingClientRect().top+window.scrollY;formSectionTitles.forEach((t,i)=>{if(t.getBoundingClientRect().top+window.scrollY<=y+20)currentIndex=i})}else{const y=window.scrollY+120;formSectionTitles.forEach((t,i)=>{if(t.getBoundingClientRect().top+window.scrollY<=y)currentIndex=i})}if(currentIndex<=0){window.scrollTo({top:0,behavior:"smooth"});return}const target=formSectionTitles[currentIndex-1];target.scrollIntoView({behavior:"smooth",block:"start"});setTimeout(()=>{const focusable=target.parentElement?.querySelector("input,select,textarea");if(focusable)focusable.focus({preventScroll:true})},350)}
document.querySelectorAll(".nav[data-target]").forEach(b=>b.onclick=()=>showSection(b.dataset.target));document.querySelectorAll("[data-open]").forEach(b=>b.onclick=()=>showSection(b.dataset.open));
$("saveProfile").onclick=saveProfileSettings;
$("profilePhotoInput").addEventListener("change",e=>{const file=e.target.files?.[0];if(!file)return;if(!file.type.startsWith("image/"))return;const reader=new FileReader();reader.onload=()=>{const image=new Image();image.onload=()=>{const size=320,canvas=document.createElement("canvas");canvas.width=size;canvas.height=size;const ctx=canvas.getContext("2d");ctx.clearRect(0,0,size,size);const scale=Math.max(size/image.width,size/image.height),w=image.width*scale,h=image.height*scale;ctx.drawImage(image,(size-w)/2,(size-h)/2,w,h);const dataUrl=canvas.toDataURL("image/jpeg",.82);$("profilePhoto").src=dataUrl;$("profilePhoto").classList.add("has-photo");$("profileInitials").classList.add("hide");let data={};try{data=JSON.parse(localStorage.getItem(profileKey(activeUserUid))||"{}")}catch{};data.photo=dataUrl;try{localStorage.setItem(profileKey(activeUserUid),JSON.stringify(data));$("profileStatus").textContent="Photo updated.";setTimeout(()=>$("profileStatus").textContent="",1800)}catch{$("profileStatus").textContent="Photo is too large to save."}};image.src=reader.result};reader.readAsDataURL(file)});
$("darkThemeToggle").addEventListener("change",e=>saveThemeSetting(e.target.checked));
initSmsBroadcast();
onAuthStateChanged(auth,u=>{if(unsub){unsub();unsub=null}if(!u){$("auth").classList.remove("hide");$("app").classList.add("hide");return}$("auth").classList.add("hide");$("app").classList.remove("hide");$("userEmail").textContent=u.email||"";loadProfileSettings(u.uid,u.email||"");let ref=collection(db,"users",u.uid,"patients");unsub=onSnapshot(query(ref,orderBy("createdAt","desc")),s=>{records=s.docs.map(d=>({id:d.id,...d.data()}));render();renderSmsPatients();recent();stats()},e=>{$("records").innerHTML='<p class="error">Could not load records. Publish the included Firestore rules and confirm Firestore exists.</p>';console.error(e)})});
patientForm.addEventListener("keydown", e => {
  if (e.key !== "Enter" || e.ctrlKey || e.altKey || e.metaKey) return;
  const el = e.target;
  if (!el.matches("input, select, textarea")) return;
  // Enter creates a new line in every textarea. Normal fields use Enter to move to the next field.
  if (el.tagName === "TEXTAREA") return;
  e.preventDefault();
  const fields = [...patientForm.querySelectorAll("input:not([type=hidden]):not([disabled]), select:not([disabled]), textarea:not([disabled])")];
  const index = fields.indexOf(el);
  const next = fields[index + 1];
  if (next) {
    next.focus();
    if (next.tagName === "INPUT" && next.type !== "date" && typeof next.select === "function") next.select();
  }
});
$("patientForm").onsubmit=async e=>{e.preventDefault();$("message").textContent="Saving...";let u=auth.currentUser;if(!u)return;syncAge();let data={};ids.forEach(i=>data[i]=$(i).value.trim());data.age=data.age||"0 Years, 0 Months, 0 Days";data.ageYears=data.ageYears||"0";data.ageMonths=data.ageMonths||"0";data.ageDays=data.ageDays||"0";try{let path=["users",u.uid,"patients"];if($("recordId").value)await updateDoc(doc(db,...path,$("recordId").value),{...data,updatedAt:serverTimestamp()});else await addDoc(collection(db,...path),{...data,createdAt:serverTimestamp(),updatedAt:serverTimestamp()});reset();$("message").textContent="Patient record saved successfully."}catch(x){console.error(x);$("message").textContent="Save failed. Publish firestore.rules and check Firebase.";$("message").className="error"}};
function render(){
  const t=$("search").value.toLowerCase().trim();
  const a=records.filter(r=>Object.values(r).join(" ").toLowerCase().includes(t));
  $("records").innerHTML=a.length?a.map(r=>`<article class="record">
    <div class="rt"><div><h3>${esc(r.name||"Unnamed")}</h3><small>${esc(r.contact||"No phone")} · Age ${esc(r.age??"—")} · ${esc(r.patientDate||"—")}</small></div>
    <div><button class="secondary small" data-e="${r.id}">Edit</button> <button class="danger small" data-d="${r.id}">Delete</button></div></div>
    <p><b>RE:</b> ${esc([r.bcvaReSph,r.bcvaReCyl,r.bcvaReAxis,r.bcvaReVa].filter(Boolean).join(" / ")||"—")} &nbsp; <b>LE:</b> ${esc([r.bcvaLeSph,r.bcvaLeCyl,r.bcvaLeAxis,r.bcvaLeVa].filter(Boolean).join(" / ")||"—")}</p>
    <details class="full-details"><summary>View all patient details</summary>
      <div class="details-grid">
        <div class="detail-section"><h4>Personal Details</h4><div class="detail-list">
          <div><b>Patient Name</b><span>${esc(r.name||"—")}</span></div><div><b>Age</b><span>${esc(r.age??"—")}</span></div>
          <div><b>Date</b><span>${esc(r.patientDate||"—")}</span></div><div><b>Contact</b><span>${esc(r.contact||"—")}</span></div>
          <div><b>Address</b><span>${esc(r.address||"—")}</span></div><div><b>Gender</b><span>${esc(r.gender||"—")}</span></div>
          <div><b>Occupation</b><span>${esc(r.occupation||"—")}</span></div>
        </div></div>

        <div class="detail-section wide-detail"><h4>Patient Refraction Details</h4>
          <div class="detail-table">
            <div class="detail-table-head"><span>Test</span><span>RE</span><span>LE</span></div>
            <div class="complaint-detail"><b>Presenting Complaint (C/C)</b><span>${esc(r.presentingComplaint || [r.ccRe,r.ccLe].filter(Boolean).join(" / ") || "—")}</span></div>
            <div><b>UCVA</b><span>${esc(r.ucvaRe||"—")}</span><span>${esc(r.ucvaLe||"—")}</span></div>
            <div><b>PH</b><span>${esc(r.phRe||"—")}</span><span>${esc(r.phLe||"—")}</span></div>
            <div><b>Dry Retinoscopy</b><span>${esc(r.dryRe||"—")}</span><span>${esc(r.dryLe||"—")}</span></div>
            <div><b>Wet Retinoscopy</b><span>${esc(r.wetRe||"—")}</span><span>${esc(r.wetLe||"—")}</span></div>
          </div>
          <div class="detail-subgrid">
            <div><h5>BCVA — RE</h5><p>SPH: ${esc(r.bcvaReSph||"—")} | CYL: ${esc(r.bcvaReCyl||"—")} | AXIS: ${esc(r.bcvaReAxis||"—")} | VA: ${esc(r.bcvaReVa||"—")}</p></div>
            <div><h5>BCVA — LE</h5><p>SPH: ${esc(r.bcvaLeSph||"—")} | CYL: ${esc(r.bcvaLeCyl||"—")} | AXIS: ${esc(r.bcvaLeAxis||"—")} | VA: ${esc(r.bcvaLeVa||"—")}</p></div>
            <div><h5>PG — RE</h5><p>SPH: ${esc(r.pgReSph||"—")} | CYL: ${esc(r.pgReCyl||"—")} | AXIS: ${esc(r.pgReAxis||"—")} | VA: ${esc(r.pgReVa||"—")}</p></div>
            <div><h5>PG — LE</h5><p>SPH: ${esc(r.pgLeSph||"—")} | CYL: ${esc(r.pgLeCyl||"—")} | AXIS: ${esc(r.pgLeAxis||"—")} | VA: ${esc(r.pgLeVa||"—")}</p></div>
            <div><h5>BCVA — ADD</h5><p>RE: ${esc(r.bcvaAddRe||"—")} | LE: ${esc(r.bcvaAddLe||"—")}</p></div>
            <div><h5>BCVA — PD</h5><p>${esc(r.bcvaPd||"—")}</p></div>
            <div><h5>PG — ADD</h5><p>RE: ${esc(r.pgAddRe||"—")} | LE: ${esc(r.pgAddLe||"—")}</p></div>
          </div>
        </div>

        <div class="detail-section"><h4>Clinical Details</h4><div class="detail-list">
          <div><b>Systemic Details</b><span>${esc(r.systemicDetails||"—")}</span></div><div><b>Ocular History</b><span>${esc(r.ocularHistory||"—")}</span></div>
          <div><b>SCH I</b><span>RE: ${esc(r.sch1Re||"—")} | LE: ${esc(r.sch1Le||"—")}</span></div>
          <div><b>SCH II</b><span>RE: ${esc(r.sch2Re||"—")} | LE: ${esc(r.sch2Le||"—")}</span></div>
          <div><b>BP</b><span>${esc(r.bp||"—")}</span></div>
          <div><b>Color Vision</b><span>RE: ${esc(r.colorVisionRe||"—")} | LE: ${esc(r.colorVisionLe||"—")}</span></div>
          <div><b>IOP</b><span>RE: ${esc(r.iopRe||"—")} | LE: ${esc(r.iopLe||"—")}</span></div>
          <div><b>Examiner</b><span>${esc(r.examiner||"—")}</span></div><div><b>Treatment</b><span>${esc(r.diagnosis||"—")}</span></div><div><b>Diagnosis</b><span>${esc(r.diagnosisFinal||"—")}</span></div>
        </div></div>

        <div class="detail-section"><h4>Lens and Frame Details</h4><div class="detail-list">
          <div><b>Right Eye (OD)</b><span>SPH: ${esc(r.lensReSph||"—")} | CYL: ${esc(r.lensReCyl||"—")} | AXIS: ${esc(r.lensReAxis||"—")} | VA: ${esc(r.lensReVa||"—")} | ADD: ${esc(r.lensReAdd||"—")}</span></div>
          <div><b>Left Eye (OS)</b><span>SPH: ${esc(r.lensLeSph||"—")} | CYL: ${esc(r.lensLeCyl||"—")} | AXIS: ${esc(r.lensLeAxis||"—")} | VA: ${esc(r.lensLeVa||"—")} | ADD: ${esc(r.lensLeAdd||"—")}</span></div>
          <div><b>Lens Type</b><span>${esc(r.lensType||"—")}</span></div><div><b>Lens Materials</b><span>${esc(r.lensMaterial||"—")}</span></div><div><b>Lens Coating</b><span>${esc(r.lensCoating||"—")}</span></div><div><b>Other Coating Details</b><span>${esc(r.lensCoatingOther||"—")}</span></div><div><b>Remarks</b><span>${esc(r.lensRemarks||"—")}</span></div><div><b>Frame Type</b><span>${esc(r.frameType||"—")}</span></div><div><b>Other Frame Details</b><span>${esc(r.frameOther||"—")}</span></div>
        </div></div>

        <div class="detail-section"><h4>Payment Details</h4><div class="detail-list">
          <div><b>Frame Amount</b><span>${esc(r.frameAmount??"0")}</span></div><div><b>Lens Amount</b><span>${esc(r.lensAmount??"0")}</span></div>
          <div><b>Medicines</b><span>${esc(r.medicinesAmount??"0")}</span></div><div><b>Clinical Test</b><span>${esc(r.clinicalTestAmount??"0")}</span></div>
          <div><b>Others</b><span>${esc(r.othersAmount??"0")}</span></div><div><b>Total</b><span>${esc(r.totalAmount??"0")}</span></div>
          <div><b>Advance</b><span>${esc(r.advanceAmount??"0")}</span></div><div><b>Remaining</b><span>${esc(r.remainingAmount??((Number(r.totalAmount)||0)-(Number(r.advanceAmount)||0)))}</span></div>
        </div></div>

        <div class="detail-section wide-detail"><h4>Additional Notes, Medicines & Suggestions</h4><div class="notes-detail-grid">
          <div><h5>Additional Notes</h5><p>${esc(r.additionalNotes||"—")}</p></div>
          <div><h5>Medicines Prescribed</h5><p>${esc(r.medicines||"—")}</p></div>
          <div><h5>Suggestions</h5><p>${esc(r.suggestions||"—")}</p></div>
        </div></div>
      </div>
    </details>
  </article>`).join(""):'<div class="empty">No patient records found.</div>';
  document.querySelectorAll("[data-e]").forEach(b=>b.onclick=()=>edit(b.dataset.e));
  document.querySelectorAll("[data-d]").forEach(b=>b.onclick=()=>remove(b.dataset.d));
}
function recent(){$("recent").innerHTML=records.slice(0,5).map(r=>`<div class="recent"><b>${esc(r.name||"Unnamed")}</b><small>${esc(r.contact||"")}</small><time>${esc(r.patientDate||"—")}</time></div>`).join("")||'<p>No patients yet.</p>'}function stats(){$("total").textContent=records.length;$("today").textContent=records.filter(r=>r.patientDate===today()).length;$("dashTotal").textContent=records.length;$("dashToday").textContent=records.filter(r=>r.patientDate===today()).length}function edit(id){let r=records.find(x=>x.id===id);if(!r)return;$("recordId").value=id;ids.forEach(i=>$(i).value=r[i]??"");if(r.ageYears!==undefined){$("ageYears").value=r.ageYears??"";$("ageMonths").value=r.ageMonths??"";$("ageDays").value=r.ageDays??""}else if(r.age!==undefined){const a=String(r.age);const match=a.match(/(\d+)\s*Years?,?\s*(\d+)\s*Months?,?\s*(\d+)\s*Days?/i);if(match){$("ageYears").value=match[1];$("ageMonths").value=match[2];$("ageDays").value=match[3]}else{$("ageYears").value=a.replace(/\D/g,"")||"0";$("ageMonths").value="0";$("ageDays").value="0"}}syncAge();calculateTotal();$("cancel").classList.remove("hide");showSection("formCard")}async function remove(id){if(!confirm("Delete this patient record permanently?"))return;let u=auth.currentUser;try{await deleteDoc(doc(db,"users",u.uid,"patients",id))}catch(x){alert("Could not delete the record.")}}function reset(){$("patientForm").reset();$("recordId").value="";syncAge();$("totalAmount").value="0.00";$("remainingAmount").value="0.00";$("patientDate").value=today();$("cancel").classList.add("hide");toggleLensCoatingOther();$("message").textContent="";$("message").className=""};function esc(v){return String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]))}
