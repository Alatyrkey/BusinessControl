export function getMaxInitData() {
  const webApp = window.WebApp;

  if (!webApp) {
    throw new Error("MAX Bridge не найден");
  }

  const initData = webApp.initData;

  if (!initData) {
    throw new Error(
      "MAX initData отсутствует. Откройте приложение внутри MAX.",
    );
  }

  return initData;
}