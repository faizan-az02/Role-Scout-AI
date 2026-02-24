(() => {
  const form = document.getElementById("lookup-form");
  const companyInput = document.getElementById("company");
  const roleInput = document.getElementById("role");
  const errorBox = document.getElementById("error-box");
  const resultPlaceholder = document.getElementById("result-placeholder");
  const resultContent = document.getElementById("result-content");
  const detailsBackdrop = document.getElementById("details-backdrop");
  const detailsBody = document.getElementById("details-body");
  const detailsClose = document.querySelector(".modal-close");
  const submitButton = form.querySelector("button[type='submit']");
  const progressBarWrap = document.getElementById("progress-bar-wrap");
  const introLoader = document.getElementById("intro-loader");
  const introQuote = document.getElementById("intro-quote");
  const runTip = document.getElementById("run-tip");
  const runTipText = document.getElementById("run-tip-text");
  const reportForm = document.getElementById("report-form");
  const reportPayloadInput = document.getElementById("report-payload");
  const openReportBtn = document.getElementById("open-report-btn");

  let lastResult = null;

  const warmupQuotes = [
    "Untangling leadership layers one title at a time.",
    "Connecting dots between profiles, press, and people pages…",
    "Filtering signal from noise across the org tree.",
    "Cross-referencing roles so guesses don’t sneak in.",
    "Tracking the real decision-maker behind the headline.",
  ];
  
  const runTips = [
    "Words matter more than you think.",
    "Sharp titles, sharper results.",
    "Signal lives in the details.",
    "Say it clean. Get it clean.",
    "One tweak can change everything.",
  ];

  if (introLoader && introQuote) {
    const picked =
      warmupQuotes[Math.floor(Math.random() * warmupQuotes.length)] ?? "";
    introQuote.textContent = picked;

    // Give the backend a moment to warm up before interaction
    window.setTimeout(() => {
      introLoader.classList.add("intro-loader--hide");
    }, 1800);
  }

  function setLoading(isLoading) {
    if (isLoading) {
      submitButton.classList.add("loading");
      submitButton.setAttribute("disabled", "disabled");
      if (progressBarWrap) progressBarWrap.classList.add("visible");
      if (runTip && runTipText) {
        const picked =
          runTips[Math.floor(Math.random() * runTips.length)] ?? "";
        runTipText.textContent = picked;
        runTip.classList.add("visible");
      }
    } else {
      submitButton.classList.remove("loading");
      submitButton.removeAttribute("disabled");
      if (progressBarWrap) progressBarWrap.classList.remove("visible");
      if (runTip) {
        runTip.classList.remove("visible");
      }
    }
  }

  function showError(message) {
    errorBox.textContent = message;
    errorBox.classList.remove("hidden");
  }

  function clearError() {
    errorBox.classList.add("hidden");
    errorBox.textContent = "";
  }

  function confidenceClass(score) {
    if (typeof score !== "number" || Number.isNaN(score)) return "confidence--low";
    if (score > 0.8) return "confidence--high";
    if (score >= 0.6) return "confidence--medium";
    return "confidence--low";
  }

  function formatScore(score) {
    if (typeof score !== "number" || Number.isNaN(score)) return "N/A";
    return score.toFixed(2);
  }

  function openDetails(html) {
    detailsBody.innerHTML = html;
    detailsBackdrop.classList.remove("hidden");
  }

  function closeDetails() {
    detailsBackdrop.classList.add("hidden");
    detailsBody.innerHTML = "";
  }

  function renderResult(data) {
    lastResult = data;
    resultPlaceholder.classList.add("hidden");
    resultContent.classList.remove("hidden");

    if (data.error) {
      resultContent.innerHTML = `
        <div class="alert alert--error">
          ${data.error}
        </div>
      `;
      return;
    }

    const fullName =
      data.first_name && data.last_name
        ? `${data.first_name} ${data.last_name}`
        : "N/A";

    const currentTitle = data.current_title || "Couldn't Fetch Title";

    const confidence = typeof data.confidence_score === "number" ? data.confidence_score : 0;
    const scoreClass = confidenceClass(confidence);
    const confidencePercent = Math.round(
      typeof confidence === "number" && !Number.isNaN(confidence)
        ? Math.max(0, Math.min(1, confidence)) * 100
        : 0
    );

    const validationSources = Array.isArray(data.validation_sources)
      ? data.validation_sources
      : [];

    const primarySource = data.primary_source || null;
    const isCached = Boolean(data.cache);

    resultContent.innerHTML = `
      <div class="result-item result-item--primary" style="flex: 1 1 auto;">
        <span class="result-label">Person</span>
        <span class="result-value result-person-name">${fullName}</span>
        <span class="result-label" style="margin-top:0.4rem;">Current title</span>
        <span class="result-value result-person-title">${currentTitle}</span>
        <div class="confidence-summary">
          <div class="confidence-summary-header">
            <span class="confidence-summary-label">Confidence</span>
            <span class="confidence-summary-value">${formatScore(
              confidence
            )}</span>
          </div>
          <div class="confidence-bar">
            <div
              class="confidence-bar-fill ${scoreClass}"
              style="width: ${confidencePercent}%;"
            ></div>
          </div>
          <div class="confidence-bar-percent">${confidencePercent}%</div>
        </div>
        <button type="button" class="details-link">Show complete info</button>
      </div>
    `;

    const detailsLink = resultContent.querySelector(".details-link");
    if (detailsLink) {
      detailsLink.addEventListener("click", () => {
        const primarySourceHtml = primarySource
          ? `<a href="${primarySource}" target="_blank" rel="noopener noreferrer">${primarySource}</a>`
          : "N/A";

        const sourcesCount = validationSources.length;

        const sourcesListItems = validationSources
          .map(
            (url) =>
              `<li><a href="${url}" target="_blank" rel="noopener noreferrer">${url}</a></li>`
          )
          .join("");

        const sourcesRow = sourcesListItems
          ? `<tr>
               <th>Source URLs</th>
               <td colspan="3">
                 <ul class="sources-list">
                   ${sourcesListItems}
                 </ul>
               </td>
             </tr>`
          : "";

        openDetails(`
          <div class="details-table-wrapper">
            <table class="details-table">
              <tbody>
                <tr>
                  <th>Person</th>
                  <td>${fullName}</td>
                  <th>Current Title</th>
                  <td>${data.current_title || "N/A"}</td>
                </tr>
                <tr>
                  <th>Company</th>
                  <td>${data.company || "N/A"}</td>
                  <th>Confidence score</th>
                  <td>
                    <span class="result-badge ${scoreClass}">
                      ${formatScore(confidence)}
                    </span>
                  </td>
                </tr>
                <tr>
                  <th>Attempts</th>
                  <td>${data.attempts ?? "N/A"}</td>
                  <th>Validation Sources</th>
                  <td>${sourcesCount}</td>
                </tr>
                <tr>
                  <th>Primary Source</th>
                  <td colspan="3">${primarySourceHtml}</td>
                </tr>
                <tr>
                  <th>Cached</th>
                  <td colspan="3">${isCached ? "Yes" : "No"}</td>
                </tr>
                ${sourcesRow}
              </tbody>
            </table>
          </div>
        `);
      });
    }
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearError();

    const company = companyInput.value.trim();
    const role = roleInput.value.trim();

    if (!company || !role) {
      showError("Please provide both a company and a role.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch("/lookup", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ company, role }),
      });

      const data = await response.json();

      if (!response.ok) {
        const message = data && data.error ? data.error : "Lookup failed.";
        showError(message);
        resultContent.classList.add("hidden");
        resultPlaceholder.classList.remove("hidden");
        return;
      }

      renderResult(data);
    } catch (error) {
      console.error(error);
      showError("Network or server error while performing lookup.");
    } finally {
      setLoading(false);
    }
  });

  detailsBackdrop.addEventListener("click", (event) => {
    if (event.target === detailsBackdrop) {
      closeDetails();
    }
  });

  if (detailsClose) {
    detailsClose.addEventListener("click", () => {
      closeDetails();
    });
  }

  if (openReportBtn && reportForm && reportPayloadInput) {
    openReportBtn.addEventListener("click", () => {
      if (!lastResult) return;
      try {
        reportPayloadInput.value = JSON.stringify(lastResult);
        reportForm.submit();
      } catch (e) {
        console.error("Failed to submit report form", e);
      }
    });
  }

  document.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const company = chip.getAttribute("data-company");
      const role = chip.getAttribute("data-role");
      if (company) companyInput.value = company;
      if (role) roleInput.value = role;
      companyInput.focus();
    });
  });
})();

