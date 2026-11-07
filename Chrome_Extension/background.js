
/* Tracks actual Chrome download events. Does not bypass permissions or publisher limits. */
const get=async()=> (await chrome.storage.local.get(["dlq_state"])).dlq_state||null;
const save=async s=>chrome.storage.local.set({dlq_state:s});
chrome.downloads.onCreated.addListener(async item=>{
  const s=await get();
  if(!s||!s.running||s.phase!=="requested"||Date.now()-s.sentAt>60000)return;
  const current=await get(); // do not associate older/unrelated downloads
  if(!current||current.phase!=="requested")return;
  await save({...current,phase:"downloading",downloadId:item.id,lastFilename:item.filename||""});
  const results=await chrome.downloads.search({id:item.id});
  if(results[0]&&results[0].state==="complete"){
    const t=await get();if(t?.downloadId===item.id)await save({...t,phase:"success"});
  }
});
chrome.downloads.onChanged.addListener(async change=>{
  if(!change.state)return;
  const s=await get();
  if(!s||!s.running||s.downloadId!==change.id)return;
  const status=change.state.current;
  if(status==="complete"||status==="interrupted")
    await save({...s,phase:status==="complete"?"success":"error",
      lastError:status==="interrupted"?"Chrome interrupted the download":""});
});
