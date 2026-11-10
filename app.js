(() => {
 const translations={
 en:{alerts:'Alerts & Follow-up',smart:'Smart Care Tools',elder:'＋ Elderly mode',elderOn:'✓ Elderly mode on'},
 hi:{alerts:'अलर्ट और फॉलो-अप',smart:'स्मार्ट केयर टूल्स',elder:'＋ बुज़ुर्ग मोड',elderOn:'✓ बुज़ुर्ग मोड चालू'},
 pa:{alerts:'ਅਲਰਟ ਅਤੇ ਫਾਲੋ-ਅੱਪ',smart:'ਸਮਾਰਟ ਕੇਅਰ ਟੂਲ',elder:'＋ ਬਜ਼ੁਰਗ ਮੋਡ',elderOn:'✓ ਬਜ਼ੁਰਗ ਮੋਡ ਚਾਲੂ'},
 bn:{alerts:'সতর্কতা ও ফলো-আপ',smart:'স্মার্ট কেয়ার টুল',elder:'＋ প্রবীণ মোড',elderOn:'✓ প্রবীণ মোড চালু'},
 ta:{alerts:'எச்சரிக்கைகள் மற்றும் தொடர்கவனம்',smart:'ஸ்மார்ட் பராமரிப்பு கருவிகள்',elder:'＋ மூத்தோர் பயன்முறை',elderOn:'✓ மூத்தோர் பயன்முறை இயக்கம்'},
 te:{alerts:'హెచ్చరికలు మరియు ఫాలో-అప్',smart:'స్మార్ట్ కేర్ టూల్స్',elder:'＋ వృద్ధుల మోడ్',elderOn:'✓ వృద్ధుల మోడ్ ఆన్'},
 mr:{alerts:'सूचना आणि फॉलो-अप',smart:'स्मार्ट केअर साधने',elder:'＋ ज्येष्ठ मोड',elderOn:'✓ ज्येष्ठ मोड सुरू'},
 gu:{alerts:'ચેતવણીઓ અને ફોલો-અપ',smart:'સ્માર્ટ કેર ટૂલ્સ',elder:'＋ વરિષ્ઠ મોડ',elderOn:'✓ વરિષ્ઠ મોડ ચાલુ'},
 ur:{alerts:'الرٹس اور فالو اپ',smart:'اسمارٹ کیئر ٹولز',elder:'＋ بزرگ موڈ',elderOn:'✓ بزرگ موڈ آن'}};
 const picker=document.getElementById('languagePicker'), elder=document.getElementById('elderToggle');
 function lang(code){const d=translations[code]||translations.en;document.documentElement.lang=code;document.querySelectorAll('[data-i18n]').forEach(e=>{if(d[e.dataset.i18n])e.textContent=d[e.dataset.i18n]});if(elder)elder.textContent=document.body.classList.contains('elder-mode')?d.elderOn:d.elder;try{localStorage.setItem('jk-language',code)}catch(e){}}
 try{if(picker)picker.value=localStorage.getItem('jk-language')||'en'}catch(e){}
 if(picker){picker.addEventListener('change',()=>lang(picker.value));lang(picker.value)}
 function toggleElder(){document.body.classList.toggle('elder-mode');try{localStorage.setItem('jk-elder',document.body.classList.contains('elder-mode')?'1':'0')}catch(e){}if(picker)lang(picker.value)}
 try{if(localStorage.getItem('jk-elder')==='1')document.body.classList.add('elder-mode')}catch(e){}
 if(elder)elder.addEventListener('click',toggleElder);
 const toolToggle=document.getElementById('elderToggleTool');if(toolToggle)toolToggle.addEventListener('click',toggleElder);
 function enableNotifications(){if(!('Notification'in window)){alert('This browser does not support notifications.');return}Notification.requestPermission().then(p=>alert(p==='granted'?'Browser reminders enabled. Keep this page open.':'Notification permission was not granted.'))}
 ['enableNotifications','enableNotifications2'].forEach(id=>{const el=document.getElementById(id);if(el)el.addEventListener('click',enableNotifications)});
 const voice=document.getElementById('voiceTest');if(voice)voice.addEventListener('click',()=>{if('speechSynthesis'in window){speechSynthesis.cancel();speechSynthesis.speak(new SpeechSynthesisUtterance('Jeevan Kavach. Please review your medicine schedule.'))}else alert('Voice support is unavailable in this browser.')});
 // Dashboard reminders: active only while the dashboard page remains open.
 const names=[...document.querySelectorAll('.medicine-row .medicine-info strong')].map(x=>x.textContent);
 const times=[...document.querySelectorAll('.medicine-row .medicine-info small')].map(x=>(x.textContent.match(/◷\s*(\d{2}:\d{2})/)||[])[1]);
 const notified=new Set();
 function check(){if(!('Notification'in window)||Notification.permission!=='granted')return;const now=new Date(),hm=String(now.getHours()).padStart(2,'0')+':'+String(now.getMinutes()).padStart(2,'0');times.forEach((t,i)=>{const key=now.toDateString()+t+i;if(t===hm&&!notified.has(key)){new Notification('Jeevan Kavach — medicine reminder',{body:'Please review your scheduled medicine: '+names[i]});notified.add(key)}})}
 if(times.length){check();setInterval(check,15000)}
})();