
(()=>{
 if(window.__daneshlinkUniversalReady)return;
 window.__daneshlinkUniversalReady=true;
 const KEY="dlq_state", MAX_TRIES=3;
 const DEFAULT={dois:[],index:0,tries:0,running:false,phase:"idle",sentAt:0,
  inputSelector:"",submitSelector:"",history:[],maxMs:150000,waitMs:20000,downloadId:null,lastError:""};
 const get=async()=>({...DEFAULT,...((await chrome.storage.local.get(KEY))[KEY]||{})});
 const put=async s=>chrome.storage.local.set({[KEY]:s});
 const extract=text=> [...new Set((text.match(/10\.\d{4,9}\/[^\s"'<>;,]+/gi)||[])
   .map(x=>x.replace(/[)\].,;]+$/g,"").trim()))];
 const ui=document.createElement("section");
 ui.id="dlq-universal";
 ui.setAttribute("dir","rtl");
 ui.style.cssText="position:fixed;z-index:2147483647;right:12px;top:12px;width:365px;max-height:92vh;overflow:auto;background:#fff;border:2px solid #2174a9;border-radius:12px;box-shadow:0 5px 25px #0004;color:#17334b;font:13px Tahoma,Arial;padding:12px;text-align:right";
 ui.innerHTML='<div style="font-weight:bold;font-size:16px">دانش‌لینک | صف DOI عمومی</div>'+
 '<p style="margin:6px 0">هر بار فهرست دلخواه خودت را وارد کن؛ فهرست پیش‌فرض وجود ندارد.</p>'+
 '<textarea id="dlq-input" rows="5" style="width:100%;box-sizing:border-box" placeholder="DOI ها، هر کدام در یک خط"></textarea>'+
 '<input id="dlq-file" type="file" accept=".txt,.csv,.html,.json" style="width:100%;margin:5px 0">'+
 '<div style="display:flex;gap:5px;flex-wrap:wrap">'+
 '<button id="dlq-load">ثبت فهرست</button><button id="dlq-pick-input">انتخاب کادر DOI</button>'+
 '<button id="dlq-pick-button">انتخاب دکمه جست‌وجو</button></div>'+
 '<div style="margin-top:7px">فاصله پس از موفقیت (ثانیه): <input id="dlq-delay" type="number" min="5" max="120" value="20" style="width:65px"></div>'+
 '<div style="margin-top:6px;display:flex;gap:5px"><button id="dlq-start">شروع / ادامه</button>'+
 '<button id="dlq-pause">توقف</button><button id="dlq-report">گزارش CSV</button></div>'+
 '<div id="dlq-status" style="background:#eef7fb;padding:9px;border-radius:7px;margin-top:8px;white-space:pre-wrap"></div>';
 document.documentElement.appendChild(ui);
 const q=id=>ui.querySelector("#"+id);
 ui.querySelectorAll("button").forEach(b=>b.style.cssText="background:#156fa9;color:white;border:0;border-radius:6px;padding:7px;cursor:pointer");
 const stateLine=async()=>{
  const s=await get();
  q("dlq-status").textContent="پیشرفت: "+s.index+" / "+s.dois.length+
   "\nوضعیت: "+s.phase+(s.running?" (فعال)":" (متوقف)")+
   "\nDOI فعلی: "+(s.dois[s.index]||"—")+
   "\nتلاش: "+s.tries+" / "+MAX_TRIES+
   "\nتنظیم کادر: "+(s.inputSelector||"انجام نشده")+
   "\nتنظیم دکمه: "+(s.submitSelector||"انجام نشده")+
   (s.lastError?"\nخطا: "+s.lastError:"");
 };
 const css=el=>{
  if(el.id && !/^\d/.test(el.id))return "#"+CSS.escape(el.id);
  if(el.name)return el.tagName.toLowerCase()+'[name="'+CSS.escape(el.name)+'"]';
  let parts=[],node=el;
  for(let depth=0;node&&depth<5;depth++,node=node.parentElement){
   if(node.id){parts.unshift("#"+CSS.escape(node.id));break;}
   let tag=node.tagName.toLowerCase(),siblings=[...node.parentElement?.children||[]].filter(x=>x.tagName===node.tagName);
   if(siblings.length>1)tag+=":nth-of-type("+([...node.parentElement.children].filter(x=>x.tagName===node.tagName).indexOf(node)+1)+")";
   parts.unshift(tag);
  }return parts.join(" > ");
 };
 const pick=async field=>{
   q("dlq-status").textContent="روی المان موردنظر در خود سایت کلیک کن...";
   const handler=async ev=>{
    const el=ev.target;
    if(ui.contains(el))return;
    ev.preventDefault();ev.stopImmediatePropagation();
    document.removeEventListener("click",handler,true);
    await put({...await get(),[field]:css(el)});
    await stateLine();
   };
   document.addEventListener("click",handler,true);
 };
 q("dlq-pick-input").onclick=()=>pick("inputSelector");
 q("dlq-pick-button").onclick=()=>pick("submitSelector");
 q("dlq-file").onchange=async ev=>{
  const f=ev.target.files?.[0];if(f){q("dlq-input").value=await f.text();}
 };
 q("dlq-load").onclick=async()=>{
  const dois=extract(q("dlq-input").value);
  if(!dois.length){alert("DOI معتبر در متن پیدا نشد");return;}
  const s=await get();
  if(s.running){alert("ابتدا صف فعلی را متوقف کن");return;}
  await put({...s,dois,index:0,tries:0,phase:"idle",history:[],lastError:""});
  await stateLine();
 };
 q("dlq-start").onclick=async()=>{
  const s=await get();
  if(!s.dois.length){alert("اول DOI ها را ثبت کن");return;}
  if(!s.inputSelector){alert("ابتدا کادر جست‌وجوی DOI سایت را انتخاب کن");return;}
  await put({...s,running:true,waitMs:Math.max(5000,Number(q("dlq-delay").value||20)*1000)});
  await stateLine();step();
 };
 q("dlq-pause").onclick=async()=>{await put({...await get(),running:false});stateLine();};
 const csvcell=v=>'"'+String(v??"").replace(/"/g,'""')+'"';
 q("dlq-report").onclick=async()=>{
  const s=await get();
  const lines=["DOI,Status,Attempts,File,Reason"];
  for(const x of s.history)lines.push([x.doi,x.status,x.tries,x.file||"",x.error||""].map(csvcell).join(","));
  const blob=new Blob(["\ufeff"+lines.join("\r\n")],{type:"text/csv;charset=utf-8"});
  const u=URL.createObjectURL(blob),a=document.createElement("a");a.href=u;a.download="daneshlink_doi_results.csv";a.click();setTimeout(()=>URL.revokeObjectURL(u),2000);
 };
 let stepping=false;
 async function step(){
  if(stepping)return;stepping=true;
  try{
   const s=await get();
   if(!s.running)return;
   if(s.index>=s.dois.length){await put({...s,running:false,phase:"finished"});return;}
   if(s.phase==="success"){
    const done={...s,history:[...s.history,{doi:s.dois[s.index],status:"downloaded",tries:s.tries,file:s.lastFilename||""}],index:s.index+1,tries:0,phase:"idle",downloadId:null,lastError:""};
    await put(done);
    setTimeout(()=>location.reload(),done.waitMs);return;
   }
   if(s.phase==="error" || (["requested","downloading"].includes(s.phase)&&Date.now()-s.sentAt>s.maxMs)){
    if(s.tries>=MAX_TRIES){
      await put({...s,history:[...s.history,{doi:s.dois[s.index],status:"failed",tries:s.tries,error:s.lastError||"Download timeout"}],
      index:s.index+1,tries:0,phase:"idle",lastError:"",downloadId:null});
    }else{
      await put({...s,phase:"idle",downloadId:null,lastError:"Retry after failed download"});
    }
    setTimeout(()=>location.reload(),8000);return;
   }
   if(s.phase!=="idle")return;
   const input=document.querySelector(s.inputSelector),button=s.submitSelector?document.querySelector(s.submitSelector):null;
   if(!input){await put({...s,running:false,lastError:"DOI input not found: re-select on site"});return;}
   if(s.submitSelector&&!button){await put({...s,running:false,lastError:"Search button not found: re-select on site"});return;}
   input.focus();
   const prototype=input.tagName==="TEXTAREA"?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;
   const set=Object.getOwnPropertyDescriptor(prototype,"value")?.set;
   if(set)set.call(input,s.dois[s.index]);else input.value=s.dois[s.index];
   input.dispatchEvent(new Event("input",{bubbles:true}));input.dispatchEvent(new Event("change",{bubbles:true}));
   await put({...s,phase:"requested",sentAt:Date.now(),tries:s.tries+1,downloadId:null,lastFilename:"",lastError:""});
   if(button)button.click();
   else input.dispatchEvent(new KeyboardEvent("keydown",{key:"Enter",code:"Enter",bubbles:true}));
  }catch(e){const s=await get();await put({...s,running:false,lastError:String(e)});}
  finally{stepping=false;stateLine();}
 }
 setInterval(step,1200);
 stateLine().then(step);
})();
