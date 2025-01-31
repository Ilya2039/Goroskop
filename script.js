document.getElementById("confirmButton").addEventListener("click", function() {
    let selectedCards = ["Таро1.jpg", "Таро5.jpg", "Таро3.jpg"];  // Пример выбранных карт
    let data = JSON.stringify(selectedCards);

    // Отправка данных в Telegram WebApp
    window.Telegram.WebApp.sendData(data);

    // Сворачиваем Mini Apps
    window.Telegram.WebApp.close();
});
