document.addEventListener("DOMContentLoaded", () => {
    let tarotCards = [];
    let selectedScenario = null;
    let selectedCards = [];
    let currentIndex = 0;

    // Получаем элементы интерфейса
    const scenarioSelector = document.getElementById('scenarioSelector');
    const tarotContainer = document.getElementById('tarotContainer');
    const viewer = document.getElementById('viewer');
    const cardImage = document.getElementById('cardImage');
    const cardTitle = document.getElementById('cardTitle');
    const cardDescription = document.getElementById('cardDescription');
    const prevBtn = document.getElementById('prev');
    const nextBtn = document.getElementById('next');
    const instruction = document.getElementById('instruction');
    const summarizeBtn = document.getElementById('summarizeBtn');
    const summaryResult = document.getElementById('summaryResult');

    const scenarios = {
        love: {
            title: "Расклад на отношения",
            positions: ["Прошлое отношений", "Текущая ситуация", "Будущее отношений"]
        },
        health: {
            title: "Расклад на здоровье",
            positions: ["Прошлые проблемы", "Текущее состояние", "Рекомендации"]
        },
        money: {
            title: "Расклад на финансы",
            positions: ["Прошлые решения", "Текущая ситуация", "Будущие перспективы"]
        }
    };

    // Загрузка данных о картах из tarot.json
    fetch('tarot.json')
        .then(response => {
            if (!response.ok) {
                throw new Error(`Ошибка HTTP: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            tarotCards = data;
            createCards(); // Создаем карты после загрузки данных
        })
        .catch(error => console.error("Ошибка загрузки данных:", error));

    // Обработчики выбора сценария
    document.querySelectorAll('.scenario-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            selectedScenario = btn.dataset.scenario;
            scenarioSelector.querySelectorAll('button').forEach(b => b.classList.remove('selected-scenario'));
            btn.classList.add('selected-scenario');
            instruction.textContent = `${scenarios[selectedScenario].title}. Выберите 3 карты.`;
            tarotContainer.style.display = 'flex';
            selectedCards = [];
            resetCards();
        });
    });

    // Функция перемешивания массива
    function shuffle(array) {
        for (let i = array.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [array[i], array[j]] = [array[j], array[i]];
        }
        return array;
    }

    // Создание карт
    function createCards() {
        tarotContainer.innerHTML = '';
        const shuffledCards = shuffle([...tarotCards]).slice(0, 8);

        shuffledCards.forEach(card => {
            const cardElement = document.createElement('div');
            cardElement.classList.add('card');
            cardElement.innerHTML = `
                <div class="card-front"></div>
                <div class="card-back" style="background-image: url('images/${card.image}')"></div>
            `;
            cardElement.addEventListener('click', () => flipCard(cardElement, card.image));
            tarotContainer.appendChild(cardElement);
        });
    }

    // Сброс карт
    function resetCards() {
        selectedCards = [];
        document.querySelectorAll('.card').forEach(card => {
            card.classList.remove('flipped');
            const number = card.querySelector('.card-number');
            if (number) number.remove();
        });
        createCards();
    }

    // Функция переворачивания карты
    function flipCard(cardElement, cardImage) {
        if (selectedCards.length >= 3 && !cardElement.classList.contains('flipped')) return;

        if (cardElement.classList.contains('flipped')) {
            const index = selectedCards.findIndex(c => c.image === cardImage);
            selectedCards.splice(index, 1);
            cardElement.classList.remove('flipped');
        } else {
            const cardData = tarotCards.find(c => c.image === cardImage);
            selectedCards.push(cardData);
            cardElement.classList.add('flipped');
        }

        if (selectedCards.length === 3) {
            setTimeout(() => {
                tarotContainer.style.display = 'none';
                viewer.style.display = 'flex';
                showCard(0);
            }, 1000);
        }
    }

    // Показ детальной информации о карте
    function showCard(index) {
        currentIndex = index;
        const cardData = selectedCards[index];

        cardImage.src = `images/${cardData.image}`;
        cardTitle.textContent = `${scenarios[selectedScenario].positions[index]}: ${cardData.title}`;
        cardDescription.textContent = cardData.descriptions[selectedScenario];

        prevBtn.disabled = currentIndex === 0;
        nextBtn.disabled = currentIndex === selectedCards.length - 1;
    }

    prevBtn.addEventListener('click', () => {
        if (currentIndex > 0) showCard(currentIndex - 1);
    });

    nextBtn.addEventListener('click', () => {
        if (currentIndex < selectedCards.length - 1) showCard(currentIndex + 1);
    });

    // Функция подведения итога
    function getSummary() {
        let query = `${scenarios[selectedScenario].title}:\n\n`;
        selectedCards.forEach((card, i) => {
            query += `${scenarios[selectedScenario].positions[i]} — ${card.title}:\n${card.descriptions[selectedScenario]}\n\n`;
        });
        query += "Подведите итог расклада, объясните значение каждой карты и общий вывод.";
        return query;
    }

    summarizeBtn.addEventListener('click', () => {
        const query = getSummary();
        summaryResult.textContent = "Обработка запроса…";
        fetch('/natal/gemini', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        })
        .then(response => response.json())
        .then(data => {
            summaryResult.textContent = data.answer || "Ошибка: не получен ответ от сервера";
        })
        .catch(error => {
            console.error('Ошибка:', error);
            summaryResult.textContent = "Ошибка запроса к серверу";
        });
    });

    createCards();
});
