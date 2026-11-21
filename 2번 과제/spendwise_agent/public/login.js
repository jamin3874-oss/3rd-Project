const form = document.getElementById("login");
const input = document.getElementById("password");
const error = document.getElementById("error");
form.addEventListener("submit", async event => {
  event.preventDefault();
  const button = form.querySelector("button");
  button.disabled = true;
  error.hidden = true;
  try {
    const bytes = new TextEncoder().encode("spendwise:" + input.value);
    const response = await fetch("/session", {
      method: "POST", headers: {Authorization: "Basic " + btoa(String.fromCharCode(...bytes))}
    });
    if (response.ok) {
      input.value = "";
      location.replace("/");
      return;
    }
    error.textContent = response.status === 401 ? "가계부 비밀번호를 확인하세요." : "잠시 후 다시 시도하세요.";
  } catch {
    error.textContent = "인터넷 연결을 확인하고 다시 시도하세요.";
  }
  error.hidden = false;
  button.disabled = false;
  input.focus();
});
