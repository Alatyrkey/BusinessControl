import { useEffect, useMemo, useState } from "react";
import { getMaxInitData } from "./max.jsx";
 
const TOTAL_REQUIREMENTS = 84;
const STORAGE_KEY = "businesscontrol_businesses";
const CHECKLIST_STORAGE_KEY = "businesscontrol_checklists";
 
const ANSWERS = [
  {
    id: "yes",
    label: "Да",
    description: "Соответствует",
    className: "answer-yes",
  },
  {
    id: "no",
    label: "Нет",
    description: "Есть несоответствие",
    className: "answer-no",
  },
  {
    id: "unknown",
    label: "Не уверен",
    description: "Нужно уточнить",
    className: "answer-unknown",
  },
  {
    id: "not_applicable",
    label: "Не применимо",
    description: "Не относится к моему бизнесу",
    className: "answer-na",
  },
];

const API_BASE_URL = "https://businesscontrol-backend.onrender.com/api";

async function apiRequest(path, options = {}) {
  const initData = getMaxInitData();

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Init-Data": initData,
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    let message = "Не удалось выполнить запрос";

    try {
      const errorData = await response.json();
      message = errorData.detail || message;
    } catch {
      // Оставляем стандартное сообщение.
    }

    throw new Error(message);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

async function fetchBusinesses() {
  return apiRequest("/businesses");
}

async function createBusinessApi(name, businessType) {
  return apiRequest("/businesses", {
    method: "POST",
    body: JSON.stringify({
      name,
      business_type: businessType,
    }),
  });
}
async function deleteBusinessApi(businessId) {
  return apiRequest(`/businesses/${businessId}`, {
    method: "DELETE",
  });
}

async function createChecklistApi(businessId) {
  return apiRequest(`/businesses/${businessId}/checklists`, {
    method: "POST",
  });
}

async function fetchUnfinishedChecklistApi(businessId) {
  return apiRequest(`/businesses/${businessId}/checklists/unfinished`);
}

async function fetchChecklistApi(checklistId) {
  return apiRequest(`/checklists/${checklistId}`);
}

async function updateChecklistItemApi(checklistItemId, result) {
  return apiRequest(
    `/checklist-items/${checklistItemId}`,
    {
      method: "PATCH",
      body: JSON.stringify({
        result,
      }),
    },
  );
}
async function finishChecklistApi(checklistId) {
  return apiRequest(
    `/checklists/${checklistId}/finish`,
    {
      method: "POST",
    },
  );
}
async function fetchChecklistResultApi(checklistId) {
  return apiRequest(`/checklists/${checklistId}/result`);
}
 
function createDemoChecklist() {
  return Array.from({ length: TOTAL_REQUIREMENTS }, (_, index) => ({
    id: index + 1,
    sourcePoint: String(index + 3),
    chapter: `Глава ${Math.min(11, Math.floor(index / 8) + 1)}`,
    chapterTitle: "Демо-данные для интерфейса",
    requirement: `Демо-требование`,
    recommendation:
      "В рабочей версии здесь будет отображаться актуальное требование из backend и ссылка на источник.",
  }));
}
 
const DEMO_CHECKLIST = createDemoChecklist();
 
function getDefaultBusinesses() {
  return [
    {
      id: "demo-cafe",
      name: "Кафе «Уют»",
      type: "Кафе",
      checked: 57,
      violations: 3,
      unknown: 5,
      demo: true,
    },
    {
      id: "demo-shop",
      name: "Магазин «Продукты»",
      type: "Продовольственный магазин",
      checked: 84,
      violations: 0,
      unknown: 2,
      demo: true,
    },
  ];
}
 function normalizeBusiness(raw) {
   const checked = Number(raw?.checked) || 0;
   const violations = Number(raw?.violations) || 0;
   const unknown = Number(raw?.unknown) || 0;

   return {
     id: raw?.id ?? `business-${Date.now()}`,
     name: raw?.name ?? "",
     type: raw?.type ?? "",
     checked: Math.min(
       Math.max(checked, 0),
       TOTAL_REQUIREMENTS,
     ),
     violations: Math.max(violations, 0),
     unknown: Math.max(unknown, 0),
     demo: Boolean(raw?.demo),
  };
}
function loadBusinesses() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
 
    if (!saved) {
      return getDefaultBusinesses();
    }
 
    const parsed = JSON.parse(saved);
 
    if (!Array.isArray(parsed)) {
      return getDefaultBusinesses();
    }
 
    return parsed.map(normalizeBusiness);
  } catch {
    return getDefaultBusinesses();
  }
}
 
function saveBusinesses(businesses) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(businesses));
  } catch {
    // Демо-приложение продолжает работать без localStorage.
  }
}
 
function loadChecklists() {
  try {
    const saved = localStorage.getItem(CHECKLIST_STORAGE_KEY);
 
    if (!saved) {
      return {};
    }
 
    const parsed = JSON.parse(saved);
 
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}
 
function saveChecklists(checklists) {
  try {
    localStorage.setItem(
      CHECKLIST_STORAGE_KEY,
      JSON.stringify(checklists),
    );
  } catch {
    // Не ломаем приложение, если localStorage недоступен.
  }
}
 
function getProgressPercent(checked) {
  const safeChecked = Math.min(
    Math.max(Number(checked) || 0, 0),
    TOTAL_REQUIREMENTS,
  );
 
  return Math.round((safeChecked / TOTAL_REQUIREMENTS) * 100);
}
 
function getFirstUnansweredIndex(checklist) {
  const index = checklist.findIndex((item) => item.result == null);

  return index === -1 ? checklist.length - 1 : index;
}

function getChecklistSummary(answers) {
  const values = Object.values(answers);
 
  return {
    checked: values.length,
    yes: values.filter((value) => value === "yes").length,
    no: values.filter((value) => value === "no").length,
    unknown: values.filter((value) => value === "unknown").length,
    notApplicable: values.filter(
      (value) => value === "not_applicable",
    ).length,
  };
}
 
function ShieldIcon() {
  return (
    <svg
      className="shield-icon"
      viewBox="0 0 48 52"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        d="M24 3L42 10V23C42 35.5 34.7 45.8 24 49C13.3 45.8 6 35.5 6 23V10L24 3Z"
        fill="currentColor"
        fillOpacity="0.14"
        stroke="currentColor"
        strokeWidth="3"
      />
      <path
        d="M15.5 25.5L21.5 31.5L33.5 19.5"
        stroke="currentColor"
        strokeWidth="3.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
 
function ArrowIcon({ direction = "right" }) {
  const path =
    direction === "left"
      ? "M15 18L9 12L15 6"
      : "M9 18L15 12L9 6";
 
  return (
    <svg
      className="arrow-icon"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        d={path}
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
 
function CheckIcon() {
  return (
    <svg
      className="small-icon"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M5 12.5L9.5 17L19 7.5"
        stroke="currentColor"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
 
function CloseIcon() {
  return (
    <svg
      className="small-icon"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M7 7L17 17M17 7L7 17"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
      />
    </svg>
  );
}
 
function FileIcon() {
  return (
    <svg
      className="small-icon"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M7 3H14L19 8V21H7V3Z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
      <path
        d="M14 3V8H19"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
      <path
        d="M10 12H16M10 16H16"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  );
}
 
function HomeIcon() {
  return (
    <svg
      className="nav-icon-svg"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M4 10.5L12 4L20 10.5V20H4V10.5Z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
      <path
        d="M9 20V14H15V20"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
    </svg>
  );
}
 
function ReportIcon() {
  return (
    <svg
      className="nav-icon-svg"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M6 3H15L19 7V21H6V3Z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
      <path
        d="M15 3V7H19M9 12H16M9 16H16"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  );
}
 
function SettingsIcon() {
  return (
    <svg
      className="nav-icon-svg"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <circle
        cx="12"
        cy="12"
        r="3"
        stroke="currentColor"
        strokeWidth="1.8"
      />
      <path
        d="M19 13.5V10.5L16.9 9.9C16.7 9.4 16.5 9 16.2 8.6L17.1 6.6L14.5 5.1L13 6.6C12.5 6.5 12.2 6.5 12 6.5C11.8 6.5 11.5 6.5 11 6.6L9.5 5.1L6.9 6.6L7.8 8.6C7.5 9 7.3 9.4 7.1 9.9L5 10.5V13.5L7.1 14.1C7.3 14.6 7.5 15 7.8 15.4L6.9 17.4L9.5 18.9L11 17.4C11.5 17.5 11.8 17.5 12 17.5C12.2 17.5 12.5 17.5 13 17.4L14.5 18.9L17.1 17.4L16.2 15.4C16.5 15 16.7 14.6 16.9 14.1L19 13.5Z"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinejoin="round"
      />
    </svg>
  );
}
 
function ProgressRing({ percent }) {
  const safePercent = Math.min(Math.max(percent, 0), 100);
 
  return (
    <div
      className="progress-ring"
      style={{ "--progress": `${safePercent}%` }}
      aria-label={`Готовность ${safePercent}%`}
    >
      <div className="progress-ring-inner">
        <span>{safePercent}%</span>
      </div>
    </div>
  );
}
 
function BottomNavigation({ active, onNavigate }) {
  const items = [
    {
      id: "businesses",
      label: "Бизнесы",
      icon: <HomeIcon />,
    },
    {
      id: "reports",
      label: "Отчёты",
      icon: <ReportIcon />,
    },
    {
      id: "settings",
      label: "Настройки",
      icon: <SettingsIcon />,
    },
  ];
 
  return (
    <nav className="bottom-navigation" aria-label="Основная навигация">
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          className={`bottom-nav-item ${
            active === item.id ? "active" : ""
          }`}
          onClick={() => onNavigate(item.id)}
        >
          <span className="bottom-nav-icon">{item.icon}</span>
          <span>{item.label}</span>
        </button>
      ))}
    </nav>
  );
}
 
function ModalShell({ children, onClose, ariaLabel }) {
  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
 
    document.addEventListener("keydown", handleKeyDown);
 
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [onClose]);
 
  return (
    <div
      className="modal-backdrop"
      role="presentation"
      onMouseDown={onClose}
    >
      <div
        className="modal-card"
        role="dialog"
        aria-modal="true"
        aria-label={ariaLabel}
        onMouseDown={(event) => event.stopPropagation()}
      >
        {children}
      </div>
    </div>
  );
}
 
function DeleteBusinessModal({ business, onCancel, onConfirm }) {
  if (!business) {
    return null;
  }
 
  return (
    <ModalShell
      onClose={onCancel}
      ariaLabel="Удаление бизнеса"
    >
      <div className="modal-icon" aria-hidden="true">
        <ShieldIcon />
      </div>
 
      <h2>Удалить бизнес?</h2>
 
      <p>
        Вы действительно хотите удалить{" "}
        <strong>{business.name}</strong>?
      </p>
 
      <p className="modal-warning">
        Данные этого объекта в приложении будут удалены.
      </p>
 
      <div className="modal-actions">
        <button
          type="button"
          className="modal-button modal-button-secondary"
          onClick={onCancel}
        >
          Отмена
        </button>
 
        <button
          type="button"
          className="modal-button modal-button-primary"
          onClick={onConfirm}
        >
          Удалить
        </button>
      </div>
    </ModalShell>
  );
}
 
function AddBusinessModal({ onCancel, onConfirm }) {
  const [name, setName] = useState("");
  const [type, setType] = useState("");
 
  const handleSubmit = (event) => {
    event.preventDefault();
 
    const trimmedName = name.trim();
    const trimmedType = type.trim();
 
    if (!trimmedName || !trimmedType) {
      return;
    }
 
    onConfirm({
      name: trimmedName,
      type: trimmedType,
    });
  };
 
  return (
    <div
      className="modal-backdrop"
      role="presentation"
      onMouseDown={onCancel}
    >
      <form
        className="modal-card modal-card-form"
        onSubmit={handleSubmit}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="modal-icon" aria-hidden="true">
          <ShieldIcon />
        </div>
 
        <h2>Добавить бизнес</h2>
 
        <p>
          Укажите название и тип бизнеса, чтобы начать самопроверку.
        </p>
 
        <div className="form-fields">
          <label>
            <span>Название бизнеса</span>
 
            <input
              type="text"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder='Например, Кафе «Уют»'
              autoFocus
              maxLength={255}
            />
          </label>
 
          <label>
            <span>Тип бизнеса</span>
 
            <input
              type="text"
              value={type}
              onChange={(event) => setType(event.target.value)}
              placeholder="Например, кафе"
              maxLength={64}
            />
          </label>
        </div>
 
        <div className="modal-actions">
          <button
            type="button"
            className="modal-button modal-button-secondary"
            onClick={onCancel}
          >
            Отмена
          </button>
 
          <button
            type="submit"
            className="modal-button modal-button-primary"
            disabled={!name.trim() || !type.trim()}
          >
            Добавить
          </button>
        </div>
      </form>
    </div>
  );
}
 
function EarlyFinishModal({ checked, onCancel, onConfirm }) {
  const remaining = TOTAL_REQUIREMENTS - checked;
 
  return (
    <ModalShell
      onClose={onCancel}
      ariaLabel="Досрочное завершение проверки"
    >
      <div className="modal-icon" aria-hidden="true">
        <ShieldIcon />
      </div>
 
      <h2>Завершить проверку?</h2>
 
      <p>
        Вы проверили <strong>{checked}</strong> из{" "}
        <strong>{TOTAL_REQUIREMENTS}</strong> требований.
      </p>
 
      <p className="modal-warning">
        {remaining > 0
          ? `${remaining} требований останутся непроверенными.`
          : "Все требования уже проверены."}
      </p>
 
      <div className="modal-actions">
        <button
          type="button"
          className="modal-button modal-button-secondary"
          onClick={onCancel}
        >
          Вернуться
        </button>
 
        <button
          type="button"
          className="modal-button modal-button-primary"
          onClick={onConfirm}
        >
          Завершить
        </button>
      </div>
    </ModalShell>
  );
}
 
function BusinessesScreen({
  businesses,
  isLoading,
  error,
  onSelectBusiness,
  onAddBusiness,
  onNavigate,
}) {
  return (
    <div className="screen businesses-screen">
      <section className="hero">
        <div className="hero-glow hero-glow-one" />
        <div className="hero-glow hero-glow-two" />
 
        <div className="hero-waves" aria-hidden="true">
          <svg
            viewBox="0 0 500 300"
            preserveAspectRatio="none"
            xmlns="http://www.w3.org/2000/svg"
          >
             <path
               className="wave-layer wave-layer-cobalt"
               d="M0,190 C75,150 175,230 275,190 C375,150 450,210 500,180 L500,300 L0,300 Z"
             />

             <path
               className="wave-layer wave-layer-electric"
               d="M0,232 C100,192 190,252 300,214 C400,184 465,236 500,208 L500,300 L0,300 Z"
             />

            <path
              className="wave-layer wave-layer-violet"
              d="M0,168 C88,138 200,188 312,152 C412,122 462,164 500,142 L500,190 C375,176 250,200 125,182 C75,176 38,180 0,190 Z"
            />
          </svg>
        </div>
 
        <div className="hero-content">
          <div className="hero-icon">
            <ShieldIcon />
          </div>
 
          <div>
            <p className="hero-eyebrow">БИЗНЕСКОНТРОЛЬ</p>
            <h1>Мой бизнес</h1>
            <p className="hero-subtitle">
              Самопроверка по нормативным требованиям
            </p>
          </div>
        </div>
      </section>
 
      <main className="content">
        <div className="section-heading">
          <div>
            <p className="section-eyebrow">ВАШИ ОБЪЕКТЫ</p>
            <h2>Мой бизнес</h2>
          </div>
 
          <span className="business-count">{businesses.length}</span>
        </div>
 
        {isLoading ? (
          <div className="empty-state">
            <div className="empty-state-icon">
              <ShieldIcon />
            </div>

            <h3>Загружаем бизнесы</h3>

             <p>
              Получаем ваши объекты из системы.
            </p>
          </div>
        ) : error ? (
          <div className="empty-state">
            <div className="empty-state-icon">
              <ShieldIcon />
          </div>

          <h3>Не удалось загрузить бизнес</h3>

          <p>{error}</p>

          <button
            type="button"
            className="primary-button"
            onClick={() => window.location.reload()}
           >
            Повторить
          </button>
        </div>
      ) : businesses.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">
            <ShieldIcon />
          </div>

          <h3>Пока нет бизнесов</h3>

          <p>
            Добавьте первый бизнес, чтобы начать самопроверку.
          </p>

          <button
            type="button"
            className="primary-button"
            onClick={onAddBusiness}
          >
            Добавить бизнес
          </button>
        </div>
      ) : (
          <div className="business-list">
            {businesses.map((business) => {
              const percent = getProgressPercent(business.checked);
 
              return (
                <button
                  key={business.id}
                  type="button"
                  className="business-card"
                  onClick={() => onSelectBusiness(business.id)}
                >
                  <div className="business-card-top">
                    <div className="business-card-icon">
                      <ShieldIcon />
                    </div>
 
                    <div className="business-card-title">
                      <div className="business-title-row">
                        <h3>{business.name}</h3>
 
                        {business.demo && (
                          <span className="demo-badge">ДЕМО</span>
                        )}
                      </div>
 
                      <p>{business.type}</p>
                    </div>
 
                    <ArrowIcon />
                  </div>
 
                  <div className="business-progress">
                    <div className="progress-label">
                      <span>
                        Проверено {business.checked}/{TOTAL_REQUIREMENTS}
                      </span>
 
                      <strong>{percent}%</strong>
                    </div>
 
                    <div className="progress-track">
                      <div
                        className="progress-value"
                        style={{ width: `${percent}%` }}
                      />
                    </div>
                  </div>
 
                  <div className="business-stats">
                    <div>
                      <span>Нарушения</span>
                      <strong>{business.violations}</strong>
                    </div>
 
                    <div>
                      <span>Не уверены</span>
                      <strong>{business.unknown}</strong>
                    </div>
 
                    <div>
                      <span>Всего</span>
                      <strong>{TOTAL_REQUIREMENTS}</strong>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        )}
 
        {businesses.length > 0 && (
          <button
            type="button"
            className="add-business"
            onClick={onAddBusiness}
          >
            <span className="add-icon">
              <ShieldIcon />
            </span>
 
            <span className="add-text">
              <strong>Добавить бизнес</strong>
              <small>Новый объект для самопроверки</small>
            </span>
 
            <ArrowIcon />
          </button>
        )}
 
        <div className="info-card">
          <div className="info-card-icon">i</div>
 
          <div>
            <strong>Как это работает?</strong>
 
            <p>
              Добавьте бизнес, пройдите проверочный лист и получите
              структурированный результат с найденными
              несоответствиями.
            </p>
          </div>
        </div>
 
        <div className="demo-notice">
          <span>ДЕМО-РЕЖИМ</span>
          <p>
            Текущие карточки и проверочные пункты используются для
            демонстрации интерфейса. Реальные данные подключим к
            backend.
          </p>
        </div>
      </main>
 
      <BottomNavigation
        active="businesses"
        onNavigate={onNavigate}
      />
    </div>
  );
}
 
function BusinessScreen({
  business,
  onBack,
  onDelete,
  onStartCheck,
  onShowReports,
  onNavigate,
}) {
  if (!business) {
    return null;
  }
 
  const percent = getProgressPercent(business.checked);
 
  return (
    <div className="screen">
      <header className="detail-header">
        <button
          type="button"
          className="back-button"
          onClick={onBack}
          aria-label="Назад"
        >
          <ArrowIcon direction="left" />
        </button>
 
        <div>
          <p>БИЗНЕС</p>
          <h1>{business.name}</h1>
        </div>
 
        <button
          type="button"
          className="business-menu-button"
          onClick={onDelete}
          aria-label="Удалить бизнес"
        >
          <span className="menu-dots">•••</span>
        </button>
      </header>
 
      <main className="content detail-content">
        <section className="business-detail-card">
          <div className="business-detail-icon">
            <ShieldIcon />
          </div>
 
          <div>
            <p className="detail-label">ТИП БИЗНЕСА</p>
            <h2>{business.type}</h2>
          </div>
        </section>
 
        <section className="audit-card">
          <div className="audit-card-top">
            <div>
              <p className="section-eyebrow">САМОПРОВЕРКА</p>
              <h2>Проверочный лист</h2>
            </div>
 
            <ProgressRing percent={percent} />
          </div>
 
          <div className="audit-progress-text">
            Проверено {business.checked} из {TOTAL_REQUIREMENTS}
          </div>
 
          <p>
            Проверьте соответствие бизнеса действующим нормативным
            требованиям.
          </p>
 
          <button
            type="button"
            className="primary-button"
            onClick={onStartCheck}
          >
            {business.checked > 0 ? "Продолжить проверку" : "Начать проверку"}
            <ArrowIcon />
          </button>
        </section>
 
        <div className="detail-actions">
          <button
            type="button"
            className="action-card"
            onClick={onShowReports}
          >
            <span className="action-icon">
              <FileIcon />
            </span>
 
            <span>
              <strong>История проверок</strong>
              <small>Результаты предыдущих проверок</small>
            </span>
 
            <ArrowIcon />
          </button>
 
          <button
            type="button"
            className="action-card"
            onClick={onShowReports}
          >
            <span className="action-icon">
              <CheckIcon />
            </span>
 
            <span>
              <strong>Последний результат</strong>
              <small>
                {business.violations === 0
                  ? "Нарушений не найдено"
                  : `${business.violations} нарушений найдено`}
              </small>
            </span>
 
            <ArrowIcon />
          </button>
 
          <button
            type="button"
            className="action-card action-card-danger"
            onClick={onDelete}
          >
            <span className="action-icon">
              <CloseIcon />
            </span>
 
            <span>
              <strong>Удалить бизнес</strong>
              <small>Удалить объект из приложения</small>
            </span>
 
            <ArrowIcon />
          </button>
        </div>
      </main>
 
      <BottomNavigation
        active="businesses"
        onNavigate={onNavigate}
      />
    </div>
  );
}
 
function ChecklistScreen({
  business,
  checklist,
  answers,
  currentIndex,
  onAnswer,
  onNext,
  onBack,
  onFinishRequest,
  onNavigate,
}) {
  const item = checklist[currentIndex];
 
  if (!item) {
    return null;
  }
 
  const checked = Object.keys(answers).length;
  const percent = getProgressPercent(checked);
  const selectedAnswer = answers[item.id] ?? null;
  const isLast = currentIndex === checklist.length - 1;
 
  return (
    <div className="screen checklist-screen">
      <header className="checklist-header">
        <div className="checklist-header-row">
          <button
            type="button"
            className="back-button"
            onClick={onBack}
            aria-label="Назад к бизнесу"
          >
            <ArrowIcon direction="left" />
          </button>
 
          <div className="checklist-business-name">
            <span>САМОПРОВЕРКА</span>
            <strong>{business.name}</strong>
          </div>
 
          <button
            type="button"
            className="finish-top-button"
            onClick={onFinishRequest}
          >
            Завершить
          </button>
        </div>
 
        <div className="checklist-progress-header">
         <div>
           <strong>
             Вопрос {currentIndex + 1} из {TOTAL_REQUIREMENTS}
           </strong>
           <span>проверочных пунктов</span>
         </div>
 
         <strong>{percent}%</strong>
       </div>
 
        <div className="checklist-progress-track">
          <div
            className="checklist-progress-value"
            style={{ width: `${percent}%` }}
          />
        </div>
      </header>
 
      <main className="content checklist-content">
        <div className="checklist-demo-label">
          ДЕМО-ПУНКТ · источник: backend
        </div>
 
      <div className="question-meta">
       <span>
         Глава {item.chapter.replace("Глава ", "")}, пункт{" "}
        {item.sourcePoint}
      </span>
    </div>
 
        <section className="question-card">
          <h1>{item.requirement}</h1>
 
          <div className="recommendation-box">
            <span>Что проверить</span>
            <p>{item.recommendation}</p>
          </div>
        </section>
 
        <section className="answers-section">
          <div className="answers-title">
            <span>Ваш ответ</span>
            <small>Выберите один вариант</small>
          </div>
 
          <div className="answers-grid">
            {ANSWERS.map((answer) => {
              const active = selectedAnswer === answer.id;
 
              return (
                <button
                  key={answer.id}
                  type="button"
                  className={`answer-card ${answer.className} ${
                    active ? "selected" : ""
                  }`}
                  onClick={() => onAnswer(item.id, answer.id)}
                >
                  <span className="answer-check">
                    {active ? <CheckIcon /> : null}
                  </span>
 
                  <span className="answer-copy">
                    <strong>{answer.label}</strong>
                    <small>{answer.description}</small>
                  </span>
                </button>
              );
            })}
          </div>
        </section>
 
        <div className="question-photo">
          <div className="question-photo-icon">+</div>
 
          <div>
            <strong>Добавить фото</strong>
            <small>
              В MAX здесь подключим камеру и загрузку фото.
            </small>
          </div>
        </div>
 
        <div className="checklist-actions">
          <button
            type="button"
            className="secondary-wide-button"
            onClick={() =>
              currentIndex > 0
                ? onBack(currentIndex - 1)
                : onBack()
            }
          >
            <ArrowIcon direction="left" />
            Назад
          </button>
 
          <button
            type="button"
            className="primary-button checklist-next-button"
            disabled={!selectedAnswer}
            onClick={() => onNext(isLast)}
          >
            {isLast ? "Завершить" : "Далее"}
            {!isLast && <ArrowIcon />}
          </button>
        </div>
      </main>
    </div>
  );
}
 
function ResultScreen({
  business,
  checklistResult,
  onBack,
  onRestart,
  onNavigate,
}) {
  const summary = checklistResult ?? {
    checked: 0,
    total: TOTAL_REQUIREMENTS,
    remaining: TOTAL_REQUIREMENTS,
    yes: 0,
    no: 0,
    unknown: 0,
    not_applicable: 0,
    violations: [],
    unknown_items: [],
    chapters: [],
  };

  const remaining = summary.remaining;
  const percent = getProgressPercent(summary.checked);

  const status =
    remaining === 0
      ? "Проверка завершена"
      : "Проверка завершена досрочно";
 
  return (
    <div className="screen">
      <header className="result-header">
        <div className="result-header-icon">
          <ShieldIcon />
        </div>
 
        <p>РЕЗУЛЬТАТ ПРОВЕРКИ</p>
        <h1>{status}</h1>
        <span>{business.name}</span>
      </header>
 
      <main className="content result-content">
        <section className="result-summary-card">
          <div className="result-summary-main">
            <ProgressRing percent={percent} />
 
            <div>
              <span>Проверено</span>
              <strong>
                {summary.checked}/{TOTAL_REQUIREMENTS}
              </strong>
              <small>{percent}% проверочных пунктов</small>
            </div>
          </div>
 
          {remaining > 0 && (
            <div className="result-warning">
              <strong>{remaining}</strong>
              <span>требований остались непроверенными</span>
            </div>
          )}
        </section>
 
        <div className="result-counters">
          <div className="result-counter">
            <span className="counter-icon counter-good">
              <CheckIcon />
            </span>
            <strong>{summary.yes}</strong>
            <small>Соответствует</small>
          </div>
 
          <div className="result-counter">
            <span className="counter-icon counter-bad">
              <CloseIcon />
            </span>
            <strong>{summary.no}</strong>
            <small>Нарушения</small>
          </div>
 
          <div className="result-counter">
            <span className="counter-icon counter-unknown">?</span>
            <strong>{summary.unknown}</strong>
            <small>Не уверены</small>
          </div>
 
          <div className="result-counter">
            <span className="counter-icon counter-na">—</span>
            <strong>{summary.not_applicable}</strong>
            <small>Не применимо</small>
          </div>
        </div>
 
        <section className="result-details-card">
  <div className="result-details-header">
    <div>
      <span className="section-eyebrow">ПОДРОБНЫЙ ОТЧЁТ</span>
      <h2>Найденные несоответствия</h2>
    </div>
 
    <div className="result-details-count">
      {summary.no}
    </div>
  </div>
 
  {summary.no === 0 ? (
    <div className="result-empty-state">
      <span className="counter-icon counter-good">
        <CheckIcon />
      </span>
 
      <div>
        <strong>Несоответствий не найдено</strong>
        <p>
          Среди проверенных пунктов ответов «Нет» нет.
        </p>
      </div>
    </div>
  ) : (
    <div className="result-violations-list">
      {summary.violations.map((item) => (
        <div
          className="result-violation"
          key={item.checklist_item_id}
        >
          <div className="result-violation-number">
            {item.source_point}
          </div>

          <div className="result-violation-content">
            <strong>{item.requirement}</strong>

            <span>
              {item.chapter_title}, пункт {item.source_point}
            </span>

            <p>{item.recommendation}</p>
         </div>
       </div>
     ))}
   </div>
  )}
</section>
 
        <button
          type="button"
          className="primary-button"
          onClick={onBack}
        >
          Вернуться к бизнесу
        </button>
 
        <button
          type="button"
          className="secondary-wide-button full-width"
          onClick={onRestart}
        >
          Пройти проверку заново
        </button>
      </main>
 
      <BottomNavigation
        active="businesses"
        onNavigate={onNavigate}
      />
    </div>
  );
}
 
function ReportsScreen({ businesses, onSelectBusiness, onNavigate }) {
  return (
    <div className="screen">
      <header className="reports-header">
  <div className="reports-header-top">
    <div>
      <p className="section-eyebrow">БИЗНЕСКОНТРОЛЬ</p>
      <h1>Отчёты</h1>
      <p>Результаты ваших самопроверок</p>
    </div>
 
    <div className="reports-header-icon">
      <FileIcon />
    </div>
  </div>
 
  <div className="reports-header-summary">
    <div>
      <strong>{businesses.length}</strong>
      <span>бизнесов</span>
    </div>
 
    <div>
      <strong>
        {businesses.reduce(
          (total, business) => total + business.violations,
          0,
        )}
      </strong>
      <span>нарушений</span>
    </div>
 
    <div>
      <strong>
        {businesses.reduce(
          (total, business) => total + business.unknown,
          0,
        )}
      </strong>
      <span>требуют уточнения</span>
    </div>
  </div>
</header>
 
      <main className="content">
        {businesses.length === 0 ? (
          <div className="placeholder-card">
            <div className="placeholder-icon">
              <FileIcon />
            </div>
 
            <h2>Отчётов пока нет</h2>
 
            <p>
              Создайте бизнес и пройдите самопроверку, чтобы получить
              результат.
            </p>
          </div>
        ) : (
          <div className="reports-list">
            {businesses.map((business) => (
              <button
                type="button"
                className="report-card"
                key={business.id}
                onClick={() => onSelectBusiness(business.id)}
              >
                <div className="report-card-icon">
                  <FileIcon />
                </div>
 
                <div>
                  <strong>{business.name}</strong>
                  <small>
                    Проверено {business.checked}/{TOTAL_REQUIREMENTS}
                  </small>
                </div>
 
                <ArrowIcon />
              </button>
            ))}
          </div>
        )}
      </main>
 
      <BottomNavigation
        active="reports"
        onNavigate={onNavigate}
      />
    </div>
  );
}
 
function SettingsScreen({ onNavigate }) {
  return (
    <div className="screen">
      <header className="placeholder-header">
        <p className="section-eyebrow">БИЗНЕСКОНТРОЛЬ</p>
        <h1>Настройки</h1>
        <p>Параметры приложения</p>
      </header>
 
      <main className="content">
        <div className="settings-list">
          <div className="settings-card">
            <div>
              <strong>Нормативная база</strong>
              <small>
                СП 2.3.6.4281-26 · актуальная база подключается через
                backend
              </small>
            </div>
 
            <span className="settings-status">Готово</span>
          </div>
 
          <div className="settings-card">
            <div>
              <strong>Режим приложения</strong>
              <small>
                Сейчас используется локальный демонстрационный режим
              </small>
            </div>
 
            <span className="settings-status">Демо</span>
          </div>
        </div>
 
        <button
          type="button"
          className="secondary-wide-button full-width"
          onClick={() => onNavigate("businesses")}
        >
          Вернуться на главную
        </button>
      </main>
 
      <BottomNavigation
        active="settings"
        onNavigate={onNavigate}
      />
    </div>
  );
}
 
function App() {
  const [screen, setScreen] = useState("businesses");
  const [businesses, setBusinesses] = useState([]);
  const [checklists, setChecklists] = useState(loadChecklists);

  const [isBusinessesLoading, setIsBusinessesLoading] = useState(true);
  const [businessesError, setBusinessesError] = useState("");

  const [selectedBusinessId, setSelectedBusinessId] = useState(null);
  const [businessToDelete, setBusinessToDelete] = useState(null);
  const [isAddBusinessOpen, setIsAddBusinessOpen] = useState(false);
 
  const [currentChecklist, setCurrentChecklist] = useState(
    DEMO_CHECKLIST,
  );
  const [currentChecklistId, setCurrentChecklistId] =
    useState(null);
  const [checklistResult, setChecklistResult] = useState(null);
  const [currentAnswers, setCurrentAnswers] = useState({});
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [isEarlyFinishOpen, setIsEarlyFinishOpen] = useState(false);
 
  const selectedBusiness = useMemo(
    () =>
      businesses.find(
        (business) => business.id === selectedBusinessId,
      ) ?? null,
    [businesses, selectedBusinessId],
  );

  useEffect(() => {
    let cancelled = false;

    async function loadBusinessesFromApi() {
      setIsBusinessesLoading(true);
      setBusinessesError("");

      try {
        const data = await fetchBusinesses();

        if (!cancelled) {
          setBusinesses(data);
        }
                  } catch (error) {
        if (!cancelled) {
          setBusinessesError(
            error instanceof Error
              ? error.message
              : "Не удалось загрузить бизнес",
          );
        }
      } finally {
        if (!cancelled) {
          setIsBusinessesLoading(false);
        }
      }
    }

    loadBusinessesFromApi();

    return () => {
      cancelled = true;
    };
  }, []); 
 
   
  useEffect(() => {
    saveChecklists(checklists);
  }, [checklists]);
 
  const updateBusinessProgress = (
    businessId,
    answers,
  ) => {
    const summary = getChecklistSummary(answers);
 
    setBusinesses((currentBusinesses) =>
      currentBusinesses.map((business) =>
        business.id === businessId
          ? {
              ...business,
              checked: summary.checked,
              violations: summary.no,
              unknown: summary.unknown,
            }
          : business,
      ),
    );
  };
 
  const openBusiness = (businessId) => {
    setSelectedBusinessId(businessId);
    setScreen("business");
  };
 
  const goBackToBusinesses = () => {
    setSelectedBusinessId(null);
    setScreen("businesses");
  };
 
  const handleDeleteBusiness = async () => {
  if (!businessToDelete) {
    return;
  }

  const businessId = businessToDelete.id;

  try {
    await deleteBusinessApi(businessId);

    setBusinesses((currentBusinesses) =>
      currentBusinesses.filter(
        (business) => business.id !== businessId,
      ),
    );

    setChecklists((currentChecklists) => {
      const next = { ...currentChecklists };
      delete next[businessId];
      return next;
    });

    setBusinessToDelete(null);
    setSelectedBusinessId(null);
    setScreen("businesses");
  } catch (error) {
    setBusinessesError(
      error instanceof Error
        ? error.message
        : "Не удалось удалить бизнес",
    );
  }
};
 
  const handleAddBusiness = async ({ name, type }) => {
  try {
    const createdBusiness = await createBusinessApi(
      name,
      type,
    );

    const businessForUi = {
      ...createdBusiness,
      checked: 0,
      violations: 0,
      unknown: 0,
      demo: false,
    };

    setBusinesses((currentBusinesses) => [
      ...currentBusinesses,
      businessForUi,
    ]);

    setIsAddBusinessOpen(false);
    setSelectedBusinessId(createdBusiness.id);
    setScreen("business");
  } catch (error) {
    setBusinessesError(
      error instanceof Error
        ? error.message
        : "Не удалось создать бизнес",
    );
  }
};
const startChecklist = async () => {
  if (!selectedBusiness) {
    return;
  }

  try {
    const unfinished = await fetchUnfinishedChecklistApi(
      selectedBusiness.id,
    );

    if (unfinished) {
      const checklistItems = unfinished.items;

      const answers = Object.fromEntries(
        checklistItems
          .filter((item) => item.result != null)
          .map((item) => [item.item_id, item.result]),
      );

      setCurrentChecklistId(unfinished.checklist_id);
      setCurrentChecklist(checklistItems);
      setCurrentAnswers(answers);
      setCurrentQuestionIndex(
        getFirstUnansweredIndex(checklistItems),
      );
      setScreen("checklist");

      return;
    }

    const checklist = await createChecklistApi(
      selectedBusiness.id,
    );

    const checklistItems = await fetchChecklistApi(
      checklist.id,
    );

    setCurrentChecklistId(checklist.id);
    setCurrentChecklist(checklistItems);
    setCurrentAnswers({});
    setCurrentQuestionIndex(0);
    setScreen("checklist");
  } catch (error) {
    setBusinessesError(
      error instanceof Error
        ? error.message
        : "Не удалось начать проверку",
    );
  }
};
 
  const saveCurrentChecklist = (
    answers,
    currentIndex,
  ) => {
    if (!selectedBusiness) {
      return;
    }
 
    setChecklists((currentChecklists) => ({
      ...currentChecklists,
      [selectedBusiness.id]: {
        answers,
        currentIndex,
        updatedAt: new Date().toISOString(),
      },
    }));
 
    updateBusinessProgress(selectedBusiness.id, answers);
  };
 
 const handleAnswer = async (itemId, answer) => {
  if (!selectedBusiness) {
    return;
  }

  const currentItem = currentChecklist[currentQuestionIndex];

  if (!currentItem) {
    return;
  }

  const checklistItemId = currentItem.id;

  if (!checklistItemId) {
    setBusinessesError(
      "Не удалось определить пункт проверки",
    );
    return;
  }

  try {
    await updateChecklistItemApi(
      checklistItemId,
      answer,
    );

    const nextAnswers = {
      ...currentAnswers,
      [itemId]: answer,
    };

    setCurrentAnswers(nextAnswers);
  } catch (error) {
    setBusinessesError(
      error instanceof Error
        ? error.message
        : "Не удалось сохранить ответ",
    );
  }
};
 
  const handleNext = async (isLast) => {
    const currentItem =
      currentChecklist[currentQuestionIndex];

    if (!currentItem) {
      return;
    }

    if (!currentAnswers[currentItem.item_id] && !currentAnswers[currentItem.id]) {
      return;
    }

    if (isLast) {
      if (!currentChecklistId) {
        setBusinessesError(
          "Не удалось определить текущую проверку",
        );
        return;
      }

      try {
        await finishChecklistApi(currentChecklistId);
        setScreen("result");
      } catch (error) {
        setBusinessesError(
          error instanceof Error
            ? error.message
            : "Не удалось завершить проверку",
        );
      }

      return;
   }

   const nextIndex = currentQuestionIndex + 1;

   setCurrentQuestionIndex(nextIndex);
 };
 
  const handleChecklistBack = (targetIndex) => {
    if (typeof targetIndex === "number") {
      setCurrentQuestionIndex(targetIndex);
      return;
    }

    setScreen("business");
  };
 
  const finishEarly = async () => {
    setIsEarlyFinishOpen(false);

    if (!currentChecklistId) {
      setBusinessesError(
        "Не удалось определить текущую проверку",
      );
      return;
    }

    try {
      await finishChecklistApi(currentChecklistId);

      const result = await fetchChecklistResultApi(
        currentChecklistId,
      );

      setChecklistResult(result);
      setScreen("result");
    } catch (error) {
      setBusinessesError(
        error instanceof Error
          ? error.message
          : "Не удалось завершить проверку",
      );
    }
  };

 const restartChecklist = async () => {
   if (!selectedBusiness) {
     return;
   }

   try {
     const checklist = await createChecklistApi(
       selectedBusiness.id,
     );

     const checklistItems = await fetchChecklistApi(
       checklist.id,
     );

     setCurrentChecklistId(checklist.id);
     setCurrentChecklist(checklistItems);
     setCurrentAnswers({});
     setCurrentQuestionIndex(0);
     setScreen("checklist");
   } catch (error) {
     setBusinessesError(
       error instanceof Error
         ? error.message
         : "Не удалось начать проверку заново",
     );
   }
 };
 
 const handleNavigate = (target) => {

    if (target === "businesses") {
      setScreen("businesses");
      return;
    }
 
    if (target === "reports") {
      setScreen("reports");
      return;
    }
 
    if (target === "settings") {
      setScreen("settings");
    }
  };
 
  if (screen === "checklist" && selectedBusiness) {
    return (
      <>
        <ChecklistScreen
          business={selectedBusiness}
          checklist={currentChecklist}
          answers={currentAnswers}
          currentIndex={currentQuestionIndex}
          onAnswer={handleAnswer}
          onNext={handleNext}
          onBack={handleChecklistBack}
          onFinishRequest={() => setIsEarlyFinishOpen(true)}
          onNavigate={handleNavigate}
        />
 
        {isEarlyFinishOpen && (
          <EarlyFinishModal
            checked={Object.keys(currentAnswers).length}
            onCancel={() => setIsEarlyFinishOpen(false)}
            onConfirm={finishEarly}
          />
        )}
      </>
    );
  }
 
  if (screen === "result" && selectedBusiness) {
  return (
    <ResultScreen
      business={selectedBusiness}
      checklistResult={checklistResult}
      onBack={() => setScreen("business")}
      onRestart={restartChecklist}
      onNavigate={handleNavigate}
    />
  );
}
 
  if (screen === "business" && selectedBusiness) {
    return (
      <>
        <BusinessScreen
          business={selectedBusiness}
          onBack={goBackToBusinesses}
          onDelete={() =>
            setBusinessToDelete(selectedBusiness)
          }
          onStartCheck={startChecklist}
          onShowReports={() => setScreen("reports")}
          onNavigate={handleNavigate}
        />
 
        {businessToDelete && (
          <DeleteBusinessModal
            business={businessToDelete}
            onCancel={() => setBusinessToDelete(null)}
            onConfirm={handleDeleteBusiness}
          />
        )}
      </>
    );
  }
 
  if (screen === "reports") {
    return (
      <ReportsScreen
        businesses={businesses}
        onSelectBusiness={openBusiness}
        onNavigate={handleNavigate}
      />
    );
  }
 
  if (screen === "settings") {
    return <SettingsScreen onNavigate={handleNavigate} />;
  }
 
  return (
    <>
      <BusinessesScreen
        businesses={businesses}
        isLoading={isBusinessesLoading}
        error={businessesError}
        onSelectBusiness={openBusiness}
        onAddBusiness={() => setIsAddBusinessOpen(true)}
        onNavigate={handleNavigate}
       />
 
      {isAddBusinessOpen && (
        <AddBusinessModal
          onCancel={() => setIsAddBusinessOpen(false)}
          onConfirm={handleAddBusiness}
        />
      )}
    </>
  );
}
 
export default App;