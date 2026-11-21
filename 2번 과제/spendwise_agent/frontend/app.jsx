const { useState, useEffect, useRef } = React;
const now = new Date();
const day = new Date(now - now.getTimezoneOffset()*60000).toISOString().slice(0,10);
const initial = {merchant:"", txn_date:day, amount:""};
const won = value => value.toLocaleString("ko-KR")+"원";

async function api(path, method="GET", body){
  const response = await fetch("/api/"+path,{method, cache:"no-store",
    headers:{"X-SpendWise-Web":"1", ...(body ? {"Content-Type":"application/json"} : {})}, body:JSON.stringify(body)});
  if(response.status===401) location.replace("/");
  const data = await response.json();
  if(!response.ok) throw new Error(typeof data.detail==="string" ? data.detail : "입력값과 서버 연결을 확인하세요.");
  return data;
}

function App(){
  const [tab,setTab]=useState("개요"), [month,setMonth]=useState(day.slice(0,7));
  const [data,setData]=useState(null), [version,refresh]=useState(0);
  const [form,setForm]=useState(initial), [edit,setEdit]=useState(null);
  const [text,setText]=useState(""), [ai,setAi]=useState(false);
  const [error,setError]=useState(""), [busy,setBusy]=useState(false);
  const retry=useRef(null);
  useEffect(()=>{
    let active=true;
    setError(""); setData(null);
    Promise.all([api("data?month="+month),api("data/summary?month="+month),api("conversations")])
      .then(([rows,summary,history])=>active && setData({rows,summary,history}))
      .catch(problem=>active && setError(problem.message));
    return ()=>{active=false;};
  },[month,version]);
  async function run(event,action){
    event.preventDefault(); setBusy(true); setError("");
    try{await action();refresh(value=>value+1);}
    catch(problem){setError(problem.message);}
    finally{setBusy(false);}
  }
  function save(event){
    run(event,async()=>{
      await api(edit?"data/"+edit:"data",edit?"PUT":"POST",{...form,amount:Number(form.amount)});
      setMonth(form.txn_date.slice(0,7));setEdit(null);setForm({...initial,txn_date:form.txn_date});
    });
  }
  function send(event){
    run(event,async()=>{
      const message=(ai?"AI: ":"")+text.trim();
      if(retry.current?.message!==message || retry.current?.month!==month)
        retry.current={message,month,request_id:crypto.randomUUID()};
      await api("chat","POST",retry.current); retry.current=null;setText("");
    });
  }
  function ledger(rows){
    return rows.length ? <ul>{rows.map(row=><li key={row.id}><span><b>{row.merchant}</b>
      <small>{row.txn_date} · {row.category}</small></span><strong>{won(row.amount)}</strong>
      <button onClick={()=>{setForm({txn_date:row.txn_date,merchant:row.merchant,amount:row.amount});setEdit(row.id);setTab("거래 내역");}}>수정</button></li>)}</ul>
      : <p>이 달에 등록된 지출이 없습니다.</p>;
  }
  const summary=data?.summary;
  return <main><header><div className="brand"><i>₩</i> SpendWise</div><label>조회 월 <input type="month" value={month}
    onChange={event=>event.target.value && setMonth(event.target.value)}/></label></header>
    <nav>{["개요","거래 내역","대화"].map(name=><button key={name} aria-current={tab===name?"page":undefined} onClick={()=>setTab(name)}>{name}</button>)}
    <form method="post" action="/session/logout" style={{marginLeft:"auto"}}><button>로그아웃</button></form></nav>
    <h1>{tab==="개요"?"월간 가계부":tab}</h1>{error && <p role="alert">{error} <button onClick={()=>refresh(value=>value+1)}>새로고침</button></p>}
    {!data && !error && <p role="status">불러오는 중…</p>}
    {tab==="개요" && summary && <><section className="hero"><span>{month.replace("-",".")} · 총지출</span><h2>{won(summary.total)}</h2>
      <div>거래 {summary.count}건 · {summary.overall_remaining===null?"전체 예산 미설정":"예산 잔액 "+won(summary.overall_remaining)}</div></section>
      <div className="grid"><section><h2>분류별 지출</h2>{Object.entries(summary.by_category).sort((left,right)=>right[1]-left[1]).map(([category,amount])=>
      <div className="category" key={category}>{category}<b>{won(amount)}</b><progress max={summary.total} value={amount}/></div>)}
      {!summary.count && <p>지출을 등록하면 분류별 합계가 표시됩니다.</p>}</section><section><h2>최근 거래</h2>{ledger(data.rows.slice(0,5))}
      <button onClick={()=>setTab("거래 내역")}>거래 관리</button></section></div></>}
    {tab==="거래 내역" && <div className="grid"><section><h2>{edit?"거래 수정":"지출 등록"}</h2><form onSubmit={save}>
      {[["거래일","txn_date","date"],["상호명","merchant","text"],["금액 (원)","amount","number"]].map(([label,field,type])=>
        <label key={field}>{label}<input required type={type} min={type==="number"?1:undefined} max={type==="number"?1e12:undefined}
        maxLength={80} value={form[field]} onChange={event=>setForm({...form,[field]:event.target.value})}/></label>)}
      <button className="primary" disabled={busy}>저장</button>{edit && <button type="button" onClick={()=>{setEdit(null);setForm(initial);}}>취소</button>}</form></section>
      <section><h2>월별 거래</h2>{data && ledger(data.rows)}</section></div>}
    {tab==="대화" && <section className="chat"><h2>가계부 도우미</h2>{data && !data.history.length && <p>예산을 설정하거나 월별 지출을 물어보세요.</p>}
      {data?.history.slice().reverse().map(turn=><article key={turn.id}><b>{turn.message}</b><p>{turn.reply}</p><small>{turn.month} · {turn.tool||"도우미"}</small></article>)}
      <form onSubmit={send}><label><input type="checkbox" checked={ai} onChange={event=>setAi(event.target.checked)}/> Claude 사용</label>
      <label>메시지<input required maxLength={1996} value={text} placeholder={ai?"이번 달 소비를 알려줘":"예산 "+month+" 전체 300000"} onChange={event=>setText(event.target.value)}/></label>
      <button className="primary" disabled={busy||!text.trim()}>{busy?"처리 중…":"보내기"}</button></form></section>}</main>;
}
ReactDOM.createRoot(document.getElementById("root")).render(<App/>);
