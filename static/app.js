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

  function setLoading(isLoading) {
    if (isLoading) {
      submitButton.classList.add("loading");
      submitButton.setAttribute("disabled", "disabled");
      if (progressBarWrap) progressBarWrap.classList.add("visible");
    } else {
      submitButton.classList.remove("loading");
      submitButton.removeAttribute("disabled");
      if (progressBarWrap) progressBarWrap.classList.remove("visible");
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
        : "Unknown";

    const currentTitle = data.current_title || "Couldn't Fetch Title";

    const confidence = typeof data.confidence_score === "number" ? data.confidence_score : 0;
    const scoreClass = confidenceClass(confidence);

    const validationSources = Array.isArray(data.validation_sources)
      ? data.validation_sources
      : [];

    const primarySource = data.primary_source || null;

    resultContent.innerHTML = `
      <div class="result-item" style="flex: 1 1 auto;">
        <span class="result-label">Person</span>
        <span class="result-value result-person-name">${fullName}</span>
        <span class="result-label" style="margin-top:0.4rem;">Current title</span>
        <span class="result-value result-person-title">${currentTitle}</span>
      </div>
      <button type="button" class="details-link">Show complete info</button>
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

        openDetails(`
          <div class="result-grid">
            <div class="result-item">
              <span class="result-label">Company</span>
              <span class="result-value">${data.company || "N/A"}</span>
            </div>
            <div class="result-item">
              <span class="result-label">Current Title</span>
              <span class="result-value">${data.current_title || "N/A"}</span>
            </div>
            <div class="result-item">
              <span class="result-label">Confidence Score</span>
              <span class="result-value">
                <span class="result-badge ${scoreClass}">
                  ${formatScore(confidence)}
                </span>
              </span>
            </div>
            <div class="result-item">
              <span class="result-label">Primary Source</span>
              <span class="result-value">${primarySourceHtml}</span>
            </div>
            <div class="result-item">
              <span class="result-label">Attempts</span>
              <span class="result-value">${data.attempts ?? "N/A"}</span>
            </div>
            <div class="result-item">
              <span class="result-label">Validation Sources</span>
              <span class="result-value">${sourcesCount}</span>
            </div>
          </div>
          ${
            sourcesListItems
              ? `<div class="result-item" style="margin-top:0.75rem;">
                   <span class="result-label">Source URLs</span>
                   <ul class="sources-list">${sourcesListItems}</ul>
                 </div>`
              : ""
          }
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

