async function analyze() {
  const keyword = document.getElementById("keyword").value;
  const resultDiv = document.getElementById("result");
  resultDiv.innerHTML = "로딩 중...";

  const res = await fetch("/api/analyze", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({keyword})
  });

  const data = await res.json();
  if (data.results) {
    resultDiv.innerHTML = "";
    data.results.forEach(item => {
      resultDiv.innerHTML += `
        <h4>${item.title}</h4>
        <a href="${item.link}" target="_blank">${item.link}</a>
        <pre>${item.analysis}</pre>
        <hr/>
      `;
    });
  } else {
    resultDiv.innerHTML = "❌ 오류 발생";
  }
}

async function diagnosis() {
  const keyword = document.getElementById("keyword").value;
  const resultDiv = document.getElementById("result");
  resultDiv.innerHTML = "로딩 중...";

  const res = await fetch("/api/diagnosis", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({keyword})
  });

  const data = await res.json();
  if (data.result) {
    resultDiv.innerHTML = `<pre>${data.result}</pre>`;
  } else {
    resultDiv.innerHTML = "❌ 오류 발생";
  }

}
async function analyze() {
  const keyword = document.getElementById("keyword").value;
  const numLinks = parseInt(document.getElementById("numLinks").value);
  const resultDiv = document.getElementById("result");
  resultDiv.innerHTML = "로딩 중...";

  if (!keyword.trim()) {
    resultDiv.innerHTML = "❗ 키워드를 입력해주세요.";
    return;
  }

  if (isNaN(numLinks) || numLinks < 1 || numLinks > 20) {
    resultDiv.innerHTML = "❗ 크롤링 개수를 1~20 사이 숫자로 입력해주세요.";
    return;
  }

  const res = await fetch("/api/analyze", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({keyword, num_links: numLinks})
  });

  const data = await res.json();
  if (data.results) {
    resultDiv.innerHTML = "";
    data.results.forEach(item => {
      resultDiv.innerHTML += `
        <h4>${item.title}</h4>
        <a href="${item.link}" target="_blank">${item.link}</a>
        <pre>${item.analysis}</pre>
        <hr/>
      `;
    });
  } else {
    resultDiv.innerHTML = "❌ 오류 발생";
  }
}
