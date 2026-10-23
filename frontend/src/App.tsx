import { useEffect, useRef, useState } from 'react'

type Evidence = { photo_id: string; region_description?: string; evidence_region?: string | number[]; region_verified?: boolean; object_id_or_visual_marker?: string; description?: string }
type Row = { row_id: string; source_line: number; sku: string; label?: string; expected_qty: number; confirmed_qty: number; status: string; reason: string; evidence: Evidence[] }
type Observation = Evidence & { sku_read?: string | null; label_read?: string | null; visibility?: string; confidence_note?: string; marker?: string; object_id?: string }
type Metrics = { elapsed_seconds?: number; model?: string; provider?: string; usage?: {input_tokens?: number; output_tokens?: number} | null; cost?:{estimated_usd:number | null;basis:string;assumptions:string;pricing_url:string}; [key:string]: unknown }
type Extra = {object_id:string | null;sku_read:string | null;label_read:string | null;status:string;evidence:Evidence[];reason:string}
type Result = { rows: Row[]; observations?: Observation[]; extra_items?: Extra[]; pdf_lines?: ({line_number?:number; line?:number; source_line?:number; text:string} | string)[]; metrics?: Metrics; warnings?: string[]; [key:string]:unknown }

function Icon({name, size=20}: {name: string; size?: number}) {
  const paths: Record<string, React.ReactNode> = {
    box: <><path d="m3 7 9-5 9 5v10l-9 5-9-5Z"/><path d="m3 7 9 5 9-5M12 12v10M7.5 4.5l9 5"/></>,
    file:<><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6M8 13h8M8 17h6"/></>,
    image:<><rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8" cy="8" r="1.5"/><path d="m21 16-5-5L5 21"/></>,
    arrow:<><path d="M4 12h16m-6-6 6 6-6 6"/></>,
    check:<path d="m5 12 4 4L19 6"/>,
    search:<><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/></>,
    download:<><path d="M12 3v12m-5-5 5 5 5-5M4 17v4h16v-4"/></>,
    clock:<><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
  }
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name] || paths.box}</svg>
}
const statusLabel = (s: string) => ({matched:'Matched',identity_mismatch:'Wrong identity',quantity_mismatch:'Quantity mismatch',unverified:'Unverified'}[s] || s.replaceAll('_',' '))
const statusClass = (s:string) => s==='matched'?'matched':s==='unverified'?'unverified':'mismatch'
const pretty = (v: unknown) => typeof v === 'string' ? v : JSON.stringify(v)

export default function App() {
  const [provider,setProvider] = useState('codex')
  const [key,setKey] = useState('')
  const [pdf,setPdf] = useState<File | null>(null)
  const [photos,setPhotos] = useState<File[]>([])
  const [previews,setPreviews] = useState<string[]>([])
  const [pdfUrl,setPdfUrl] = useState('')
  const [health,setHealth] = useState<Record<string,unknown> | null>(null)
  const [result,setResult] = useState<Result | null>(null)
  const [error,setError] = useState('')
  const [busy,setBusy] = useState(false)
  const [loadingSample,setLoadingSample] = useState(false)
  const [seconds,setSeconds] = useState(0)
  const [selectedPhoto,setSelectedPhoto] = useState(0)
  const [selectedEvidence,setSelectedEvidence] = useState<Evidence | null>(null)
  const [view,setView] = useState('results')
  const resultsRef = useRef<HTMLElement>(null)
  useEffect(()=> {fetch('/api/health').then(r=>r.ok?r.json():null).then(setHealth).catch(()=>setHealth(null))},[])
  useEffect(()=> {const urls=photos.map(p=>URL.createObjectURL(p));setPreviews(urls);setSelectedPhoto(0);return()=>urls.forEach(URL.revokeObjectURL)},[photos])
  useEffect(()=> {if(!pdf){setPdfUrl('');return};const url=URL.createObjectURL(pdf);setPdfUrl(url);return()=>URL.revokeObjectURL(url)},[pdf])
  useEffect(()=> {if(!busy)return;setSeconds(0);const t=window.setInterval(()=>setSeconds(s=>s+1),1000);return()=>clearInterval(t)},[busy])
  const resetResult = () => {setResult(null);setError('');setSelectedEvidence(null)}
  function choosePdf(files: FileList | null) {if(!files?.length)return;const f=files[0];if(!f.name.toLowerCase().endsWith('.pdf')||f.size>10*1024*1024){setError('Choose a PDF up to 10 MB.');return};setPdf(f);resetResult()}
  function choosePhotos(files: FileList | null) {if(!files)return;const fs=Array.from(files);if(fs.length<1||fs.length>3||fs.some(f=>!['image/jpeg','image/png','image/webp'].includes(f.type)||f.size>10*1024*1024)){setError('Choose 1–3 JPG, PNG or WebP photos, up to 10 MB each.');return};setPhotos(fs);resetResult()}
  async function loadSample(kind: string) {
    setLoadingSample(true);resetResult()
    try {
      const names = [kind==='incorrect'?'packing_list_incorrect.pdf':'packing_list_correct.pdf',...(kind==='issue'?['photo_1.png','photo_2.png','photo_3.png']:['corrected_delivery.png'])]
      const files = await Promise.all(names.map(async name=>{const r=await fetch(`/sample-data/${name}`);if(!r.ok)throw new Error('Sample files are unavailable. Start the backend and retry.');return new File([await r.blob()],name,{type:name.endsWith('.pdf')?'application/pdf':'image/png'})}))
      setPdf(files[0]);setPhotos(files.slice(1))
    } catch(e) {setError(e instanceof Error?e.message:'Could not load samples.')} finally {setLoadingSample(false)}
  }
  async function analyze() {
    if(!pdf||!photos.length)return
    if(provider==='openai'&&!key.trim()){setError('Enter your own OpenAI API key.');return}
    setBusy(true);setError('');setResult(null);setSelectedEvidence(null)
    try {
      const data=new FormData();data.append('packing_list',pdf);photos.forEach(p=>data.append('photos',p));data.append('provider',provider);data.append('api_key',provider==='openai'?key:'')
      const r=await fetch('/api/analyze',{method:'POST',body:data})
      const body=await r.json()
      if(!r.ok)throw new Error(typeof body.detail==='string'?body.detail:(body.error || 'Analysis failed. Check the input files and try again.'))
      setResult(body);setView('results')
      window.setTimeout(()=>resultsRef.current?.scrollIntoView({behavior:'smooth',block:'nearest'}),100)
    } catch(e) {setError(e instanceof Error?e.message:'The server could not be reached. Start the backend and retry.')} finally {setBusy(false)}
  }
  function focusEvidence(e: Evidence) {setSelectedEvidence(e);const idx=Number(e.photo_id.match(/\d+/)?.[0])-1;if(Number.isFinite(idx)&&idx>=0&&idx<photos.length)setSelectedPhoto(idx);setView('evidence')}
  function download() {if(!result)return;const a=document.createElement('a');const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));a.href=url;a.download='parcelproof-analysis.json';a.click();URL.revokeObjectURL(url)}
  const rows=result?.rows || []
  const metrics=result?.metrics || {}
  const matched=rows.filter(r=>r.status==='matched').length
  const unverified=rows.filter(r=>r.status==='unverified').length
  const mismatches=rows.length-matched-unverified
  const elapsed=typeof metrics.elapsed_seconds==='number'?metrics.elapsed_seconds:undefined
  const cost=typeof metrics.cost?.estimated_usd==='number'?metrics.cost.estimated_usd:null
  const codexReady=health ? Boolean(health.codex_available && health.codex_authenticated) : null
  return <>
    <header className="topbar"><div className="brand"><div className="brandmark"><Icon name="box" size={23}/></div><span>Parcel<span className="brandlight">Proof</span></span><span className="poc">PROOF OF CONCEPT</span></div><div className="topmeta"><span className="live-dot"/>Evidence before conclusions<span className="topdivider"/>CODEBRIDGE / 2026</div></header>
    <main className="shell">
      <div className="intro"><div><div className="eyebrow">DELIVERY RECONCILIATION</div><h1>What arrived.<br/><span>What the evidence supports.</span></h1><p>Compare a packing list with delivery photos. Every finding links back to a PDF row and visible evidence.</p></div><div className="principle"><span>THE CAPTURE RULE</span><strong>One object. One marker.</strong><p>Use stable ITEM-01 style tags across photos to avoid double counting. Hidden labels stay unverified.</p></div></div>
      <div className="workspace">
        <aside className="input-panel">
          <div className="panel-heading"><span className="step">01</span><h2>Prepare an inspection</h2></div>
          <div className="auth-block"><label htmlFor="provider">Model connection</label><select id="provider" value={provider} onChange={e=>setProvider(e.target.value)} disabled={busy}><option value="codex">ChatGPT · local Codex</option><option value="openai">OpenAI API · your key</option></select>{provider==='codex'?<p className="helper"><span className={codexReady?'connection-dot':'connection-dot unknown'}/>{codexReady?'Local Codex is signed in. ':health?.codex_available?'CLI found; sign-in is needed. ':'Uses your local CLI login. '}Run <code>codex login</code> once; no password is entered here.</p>:<><label className="key-label" htmlFor="api-key">Your API key</label><input id="api-key" type="password" autoComplete="off" value={key} placeholder="sk-…" onChange={e=>setKey(e.target.value)} disabled={busy}/><p className="helper">Used for this request only. Kept in memory, never in browser storage.</p></>}</div>
          <div className="upload-section"><label className="field-title">Packing list <span>1 page · text PDF</span></label><label className={`dropzone ${pdf?'has-file':''}`}><input aria-label="Upload packing list PDF" type="file" accept="application/pdf,.pdf" onChange={e=>choosePdf(e.target.files)} disabled={busy}/><div className="upload-icon"><Icon name="file"/></div><strong>{pdf?pdf.name:'Choose a packing list'}</strong><span>{pdf?`${(pdf.size/1024).toFixed(0)} KB · Click to replace`:'Up to 5 SKUs · max 10 MB'}</span></label></div>
          <div className="upload-section"><label className="field-title">Delivery photos <span>1–3 photos</span></label><label className={`dropzone photo-drop ${photos.length?'has-file':''}`}><input aria-label="Upload delivery photos" type="file" multiple accept="image/jpeg,image/png,image/webp" onChange={e=>choosePhotos(e.target.files)} disabled={busy}/><div className="upload-icon"><Icon name="image"/></div><strong>{photos.length?`${photos.length} photo${photos.length>1?'s':''} selected`:'Choose delivery photos'}</strong><span>{photos.length?photos.map(p=>p.name).join(' · '):'JPG, PNG or WebP · max 10 MB each'}</span></label></div>
          <button className="analyze" onClick={analyze} disabled={busy||loadingSample||!pdf||!photos.length}>{busy?<><span className="spinner"/>Analyzing · {seconds}s</>:<>Analyze delivery<Icon name="arrow"/></>}</button>
          {busy&&<p className="running-note" role="status">Reading the PDF and inspecting photos with the model. This can take a minute.</p>}
          {error&&<div className="error" role="alert">{error}</div>}
          <div className="samples"><div className="sample-label">OR TRY THE SYNTHETIC TEST SET</div><div className="sample-buttons"><button onClick={()=>loadSample('issue')} disabled={busy||loadingSample}>Issue delivery<Icon name="arrow" size={14}/></button><button onClick={()=>loadSample('corrected')} disabled={busy||loadingSample}>Corrected delivery<Icon name="arrow" size={14}/></button><button onClick={()=>loadSample('incorrect')} disabled={busy||loadingSample}>Incorrect packing list<Icon name="arrow" size={14}/></button></div><p>AI-generated photos and authored PDFs. Samples load inputs; Analyze makes a real model call.</p></div>
        </aside>
        <section className="review-panel" ref={resultsRef}>
          <div className="review-header"><div className="panel-heading"><span className="step">02</span><h2>Review the evidence</h2></div>{result&&<button className="text-button" onClick={download}><Icon name="download" size={16}/>Export JSON</button>}</div>
          <div className="tabs"><button className={view==='results'?'active':''} onClick={()=>setView('results')}>Findings{result&&<span>{rows.length}</span>}</button><button className={view==='evidence'?'active':''} onClick={()=>setView('evidence')}>Photo evidence{photos.length>0&&<span>{photos.length}</span>}</button><button className={view==='document'?'active':''} onClick={()=>setView('document')}>PDF source</button></div>
          {view==='results'&&!result&&<div className="empty-state"><div className="empty-graphic"><div className="empty-file"><Icon name="file" size={38}/></div><div className="empty-connector"/><div className="empty-photo"><Icon name="image" size={38}/><span><Icon name="search" size={20}/></span></div></div><h3>A clear trail from source to finding.</h3><p>Upload your files or load a test set, then analyze.<br/>The model reads the inputs; matching rules check the result.</p><div className="legend"><span><i className="matched"/>Matched</span><span><i className="mismatch"/>Mismatch</span><span><i className="unverified"/>Unverified</span></div><div className="empty-footnote">Not visible does not mean not delivered.</div></div>}
          {view==='results'&&result&&<div className="findings"><div className="summary"><div><b>{matched}</b><span><i className="matched"/>Matched</span></div><div><b>{mismatches}</b><span><i className="mismatch"/>Mismatches</span></div><div><b>{unverified}</b><span><i className="unverified"/>Unverified</span></div><div className="time-stat"><b>{elapsed!==undefined?`${elapsed.toFixed(1)}s`:'—'}</b><span><Icon name="clock" size={12}/>Measured run</span></div></div>
            <div className="row-list">{rows.map(row=><article className="finding" key={row.row_id}><div className="finding-top"><div><div className="sku">{row.sku}</div><h3>{row.label || row.sku}</h3></div><span className={`status ${statusClass(row.status)}`}>{row.status==='matched'&&<Icon name="check" size={13}/>} {statusLabel(row.status)}</span></div><div className="finding-facts"><span><b>{row.expected_qty}</b> expected</span><span><b>{row.confirmed_qty}</b> confirmed unique</span><button onClick={()=>setView('document')} className="source-link"><Icon name="file" size={13}/>{row.row_id} · PDF line {row.source_line}</button></div><p className="reason">{row.reason}</p>{row.evidence?.length>0&&<div className="evidence-links">{row.evidence.map((e,i)=><button key={i} onClick={()=>focusEvidence(e)}><Icon name="image" size={13}/><span>{e.photo_id} · {e.region_description || e.description || pretty(e.evidence_region || 'Visible source')}</span><Icon name="arrow" size={13}/></button>)}</div>}</article>)}</div>
            {(result.extra_items?.length || 0)>0&&<div className="extras"><strong>Other visible observations</strong>{result.extra_items!.map((item,i)=><div className="extra-item" key={i}><p><span className={`status ${statusClass(item.status)}`}>{statusLabel(item.status)}</span></p><p><b>{item.object_id || 'Unmarked object'} · {item.sku_read || 'SKU unconfirmed'}</b>{item.label_read?` · ${item.label_read}`:''}</p><p>{item.reason}</p>{item.evidence?.map((e,j)=><button className="text-button" key={j} onClick={()=>focusEvidence(e)}><Icon name="image" size={12}/>{e.photo_id} · {e.region_description}</button>)}</div>)}</div>}
            {result.warnings?.length? <div className="warnings">{result.warnings.map((w,i)=><p key={i}>{w}</p>)}</div>:null}
            <div className="run-meta"><div><span>MODEL</span><strong>{metrics.model || 'See exported trace'}</strong></div><div><span>COST · ESTIMATE</span><strong>{cost!==null?`$${cost.toFixed(5)}`:metrics.provider==='codex'?'ChatGPT plan usage':'See cost assumptions'}</strong></div>{metrics.usage&&<div><span>TOKENS · RETURNED USAGE</span><strong>{metrics.usage.input_tokens?.toLocaleString()} in / {metrics.usage.output_tokens?.toLocaleString()} out</strong></div>}<p>{metrics.cost?.basis || 'Elapsed time is measured. Cost is an estimate; ChatGPT plan usage is not a per-request API bill.'}{metrics.cost?.assumptions?` ${metrics.cost.assumptions}`:''}{metrics.cost?.pricing_url&&<> <a href={metrics.cost.pricing_url} target="_blank" rel="noreferrer">Pricing source ↗</a></>}</p></div>
          </div>}
          {view==='evidence'&&<div className="photo-view">{previews.length?<><div className="photo-selector">{photos.map((p,i)=><button key={i} onClick={()=>{setSelectedPhoto(i);setSelectedEvidence(null)}} className={selectedPhoto===i?'active':''}><img src={previews[i]} alt=""/><span>photo_{i+1}</span></button>)}</div><div className="photo-title"><strong>photo_{selectedPhoto+1}</strong><span>{photos[selectedPhoto]?.name}</span></div><img className="evidence-photo" src={previews[selectedPhoto]} alt={`Delivery evidence photo ${selectedPhoto+1}`}/>{selectedEvidence&&<div className="region-note"><strong>Model-described region</strong><p>{selectedEvidence.region_description || selectedEvidence.description || pretty(selectedEvidence.evidence_region)}</p></div>}<p className="image-disclaimer">Regions are model descriptions, not verified pixel coordinates. No precision boxes are implied.</p></>:<div className="tab-empty"><Icon name="image" size={30}/><p>Choose photos to inspect the source evidence.</p></div>}</div>}
          {view==='document'&&<div className="document-view">{pdf?<><div className="document-title"><Icon name="file"/><strong>{pdf.name}</strong><a href={pdfUrl} target="_blank" rel="noreferrer">Open PDF ↗</a></div>{result?.pdf_lines?.length?<div className="source-lines">{result.pdf_lines.map((line,i)=><div key={i}><span>{typeof line==='string'?i+1:line.line_number??line.source_line??line.line??i+1}</span><code>{typeof line==='string'?line:line.text}</code></div>)}</div>:<><p className="helper">Numbered source text appears after analysis.</p><iframe title="Packing list PDF source" src={pdfUrl}/></>}</>:<div className="tab-empty"><Icon name="file" size={30}/><p>Choose a PDF to inspect the packing list.</p></div>}</div>}
        </section>
      </div>
      <footer><span>PARCELPROOF <span className="footer-slash">/</span> A focused feasibility study</span><span>1-page PDF · Up to 5 SKUs · 1–3 photos · Limited synthetic validation</span></footer>
    </main>
  </>
}
