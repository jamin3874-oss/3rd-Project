const { useState, useEffect, useRef } = React;
const now = /* @__PURE__ */ new Date();
const day = new Date(now - now.getTimezoneOffset() * 6e4).toISOString().slice(0, 10);
const initial = { merchant: "", txn_date: day, amount: "" };
const won = (value) => value.toLocaleString("ko-KR") + "\uC6D0";
async function api(path, method = "GET", body) {
  const response = await fetch("/api/" + path, {
    method,
    cache: "no-store",
    headers: body ? { "Content-Type": "application/json" } : {},
    body: JSON.stringify(body)
  });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "\uC785\uB825\uAC12\uACFC \uC11C\uBC84 \uC5F0\uACB0\uC744 \uD655\uC778\uD558\uC138\uC694.");
  return data;
}
function App() {
  const [tab, setTab] = useState("\uAC1C\uC694"), [month, setMonth] = useState(day.slice(0, 7));
  const [data, setData] = useState(null), [version, refresh] = useState(0);
  const [form, setForm] = useState(initial), [edit, setEdit] = useState(null);
  const [text, setText] = useState(""), [ai, setAi] = useState(false);
  const [error, setError] = useState(""), [busy, setBusy] = useState(false);
  const retry = useRef(null);
  useEffect(() => {
    let active = true;
    setError("");
    setData(null);
    Promise.all([api("data?month=" + month), api("data/summary?month=" + month), api("conversations")]).then(([rows, summary2, history]) => active && setData({ rows, summary: summary2, history })).catch((problem) => active && setError(problem.message));
    return () => {
      active = false;
    };
  }, [month, version]);
  async function run(event, action) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await action();
      refresh((value) => value + 1);
    } catch (problem) {
      setError(problem.message);
    } finally {
      setBusy(false);
    }
  }
  function save(event) {
    run(event, async () => {
      await api(edit ? "data/" + edit : "data", edit ? "PUT" : "POST", { ...form, amount: Number(form.amount) });
      setMonth(form.txn_date.slice(0, 7));
      setEdit(null);
      setForm({ ...initial, txn_date: form.txn_date });
    });
  }
  function send(event) {
    run(event, async () => {
      const message = (ai ? "AI: " : "") + text.trim();
      if (retry.current?.message !== message || retry.current?.month !== month)
        retry.current = { message, month, request_id: crypto.randomUUID() };
      await api("chat", "POST", retry.current);
      retry.current = null;
      setText("");
    });
  }
  function ledger(rows) {
    return rows.length ? /* @__PURE__ */ React.createElement("ul", null, rows.map((row) => /* @__PURE__ */ React.createElement("li", { key: row.id }, /* @__PURE__ */ React.createElement("span", null, /* @__PURE__ */ React.createElement("b", null, row.merchant), /* @__PURE__ */ React.createElement("small", null, row.txn_date, " \xB7 ", row.category)), /* @__PURE__ */ React.createElement("strong", null, won(row.amount)), /* @__PURE__ */ React.createElement("button", { onClick: () => {
      setForm({ txn_date: row.txn_date, merchant: row.merchant, amount: row.amount });
      setEdit(row.id);
      setTab("\uAC70\uB798 \uB0B4\uC5ED");
    } }, "\uC218\uC815")))) : /* @__PURE__ */ React.createElement("p", null, "\uC774 \uB2EC\uC5D0 \uB4F1\uB85D\uB41C \uC9C0\uCD9C\uC774 \uC5C6\uC2B5\uB2C8\uB2E4.");
  }
  const summary = data?.summary;
  return /* @__PURE__ */ React.createElement("main", null, /* @__PURE__ */ React.createElement("header", null, /* @__PURE__ */ React.createElement("div", { className: "brand" }, /* @__PURE__ */ React.createElement("i", null, "\u20A9"), " SpendWise"), /* @__PURE__ */ React.createElement("label", null, "\uC870\uD68C \uC6D4 ", /* @__PURE__ */ React.createElement(
    "input",
    {
      type: "month",
      value: month,
      onChange: (event) => event.target.value && setMonth(event.target.value)
    }
  ))), /* @__PURE__ */ React.createElement("nav", null, ["\uAC1C\uC694", "\uAC70\uB798 \uB0B4\uC5ED", "\uB300\uD654"].map((name) => /* @__PURE__ */ React.createElement("button", { key: name, "aria-current": tab === name ? "page" : void 0, onClick: () => setTab(name) }, name))), /* @__PURE__ */ React.createElement("h1", null, tab === "\uAC1C\uC694" ? "\uC6D4\uAC04 \uAC00\uACC4\uBD80" : tab), error && /* @__PURE__ */ React.createElement("p", { role: "alert" }, error, " ", /* @__PURE__ */ React.createElement("button", { onClick: () => refresh((value) => value + 1) }, "\uC0C8\uB85C\uACE0\uCE68")), !data && !error && /* @__PURE__ */ React.createElement("p", { role: "status" }, "\uBD88\uB7EC\uC624\uB294 \uC911\u2026"), tab === "\uAC1C\uC694" && summary && /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("section", { className: "hero" }, /* @__PURE__ */ React.createElement("span", null, month.replace("-", "."), " \xB7 \uCD1D\uC9C0\uCD9C"), /* @__PURE__ */ React.createElement("h2", null, won(summary.total)), /* @__PURE__ */ React.createElement("div", null, "\uAC70\uB798 ", summary.count, "\uAC74 \xB7 ", summary.overall_remaining === null ? "\uC804\uCCB4 \uC608\uC0B0 \uBBF8\uC124\uC815" : "\uC608\uC0B0 \uC794\uC561 " + won(summary.overall_remaining))), /* @__PURE__ */ React.createElement("div", { className: "grid" }, /* @__PURE__ */ React.createElement("section", null, /* @__PURE__ */ React.createElement("h2", null, "\uBD84\uB958\uBCC4 \uC9C0\uCD9C"), Object.entries(summary.by_category).sort((left, right) => right[1] - left[1]).map(([category, amount]) => /* @__PURE__ */ React.createElement("div", { className: "category", key: category }, category, /* @__PURE__ */ React.createElement("b", null, won(amount)), /* @__PURE__ */ React.createElement("progress", { max: summary.total, value: amount }))), !summary.count && /* @__PURE__ */ React.createElement("p", null, "\uC9C0\uCD9C\uC744 \uB4F1\uB85D\uD558\uBA74 \uBD84\uB958\uBCC4 \uD569\uACC4\uAC00 \uD45C\uC2DC\uB429\uB2C8\uB2E4.")), /* @__PURE__ */ React.createElement("section", null, /* @__PURE__ */ React.createElement("h2", null, "\uCD5C\uADFC \uAC70\uB798"), ledger(data.rows.slice(0, 5)), /* @__PURE__ */ React.createElement("button", { onClick: () => setTab("\uAC70\uB798 \uB0B4\uC5ED") }, "\uAC70\uB798 \uAD00\uB9AC")))), tab === "\uAC70\uB798 \uB0B4\uC5ED" && /* @__PURE__ */ React.createElement("div", { className: "grid" }, /* @__PURE__ */ React.createElement("section", null, /* @__PURE__ */ React.createElement("h2", null, edit ? "\uAC70\uB798 \uC218\uC815" : "\uC9C0\uCD9C \uB4F1\uB85D"), /* @__PURE__ */ React.createElement("form", { onSubmit: save }, [["\uAC70\uB798\uC77C", "txn_date", "date"], ["\uC0C1\uD638\uBA85", "merchant", "text"], ["\uAE08\uC561 (\uC6D0)", "amount", "number"]].map(([label, field, type]) => /* @__PURE__ */ React.createElement("label", { key: field }, label, /* @__PURE__ */ React.createElement(
    "input",
    {
      required: true,
      type,
      min: type === "number" ? 1 : void 0,
      max: type === "number" ? 1e12 : void 0,
      maxLength: 80,
      value: form[field],
      onChange: (event) => setForm({ ...form, [field]: event.target.value })
    }
  ))), /* @__PURE__ */ React.createElement("button", { className: "primary", disabled: busy }, "\uC800\uC7A5"), edit && /* @__PURE__ */ React.createElement("button", { type: "button", onClick: () => {
    setEdit(null);
    setForm(initial);
  } }, "\uCDE8\uC18C"))), /* @__PURE__ */ React.createElement("section", null, /* @__PURE__ */ React.createElement("h2", null, "\uC6D4\uBCC4 \uAC70\uB798"), data && ledger(data.rows))), tab === "\uB300\uD654" && /* @__PURE__ */ React.createElement("section", { className: "chat" }, /* @__PURE__ */ React.createElement("h2", null, "\uAC00\uACC4\uBD80 \uB3C4\uC6B0\uBBF8"), data && !data.history.length && /* @__PURE__ */ React.createElement("p", null, "\uC608\uC0B0\uC744 \uC124\uC815\uD558\uAC70\uB098 \uC6D4\uBCC4 \uC9C0\uCD9C\uC744 \uBB3C\uC5B4\uBCF4\uC138\uC694."), data?.history.slice().reverse().map((turn) => /* @__PURE__ */ React.createElement("article", { key: turn.id }, /* @__PURE__ */ React.createElement("b", null, turn.message), /* @__PURE__ */ React.createElement("p", null, turn.reply), /* @__PURE__ */ React.createElement("small", null, turn.month, " \xB7 ", turn.tool || "\uB3C4\uC6B0\uBBF8"))), /* @__PURE__ */ React.createElement("form", { onSubmit: send }, /* @__PURE__ */ React.createElement("label", null, /* @__PURE__ */ React.createElement("input", { type: "checkbox", checked: ai, onChange: (event) => setAi(event.target.checked) }), " Claude \uC0AC\uC6A9"), /* @__PURE__ */ React.createElement("label", null, "\uBA54\uC2DC\uC9C0", /* @__PURE__ */ React.createElement("input", { required: true, maxLength: 1996, value: text, placeholder: ai ? "\uC774\uBC88 \uB2EC \uC18C\uBE44\uB97C \uC54C\uB824\uC918" : "\uC608\uC0B0 " + month + " \uC804\uCCB4 300000", onChange: (event) => setText(event.target.value) })), /* @__PURE__ */ React.createElement("button", { className: "primary", disabled: busy || !text.trim() }, busy ? "\uCC98\uB9AC \uC911\u2026" : "\uBCF4\uB0B4\uAE30"))));
}
ReactDOM.createRoot(document.getElementById("root")).render(/* @__PURE__ */ React.createElement(App, null));
