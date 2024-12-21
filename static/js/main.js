function toggleFieldsByName(fieldName, show) {

    const targetFields = document.querySelectorAll(fieldName);
    toggleFields(targetFields, show);
}

function toggleFields(targetFields, show) {
    targetFields.forEach(field => {
        toggleField(field, show);
    });
}

function toggleField(field, show) {
    if (show) {
        if (field.tagName.toLowerCase() === 'label') {
            field.style.display = 'inline-block';
        } else {
            field.style.display = 'block';
        }
    } else {
        field.style.display = 'none'; // 非表示
        const inputs = field.querySelectorAll('input, select');
        inputs.forEach(input => {
            if (input.type === 'radio' || input.type === 'checkbox') {
                input.checked = false; // ラジオボタンとチェックボックスを解除
            } else if (input.tagName === 'SELECT') {
                input.selectedIndex = 0; // セレクトボックスを初期状態に戻す
            } else {
                input.value = ''; // その他の入力をクリア
            }
        });
    }
}

function toggleFieldsByWorkStatus() {
    const workStatusField = document.getElementById('id_work_status');
    const show = workStatusField.value == '0';

    toggleFieldsByName('.work-fields', show);
}

function setupToggleWorkStatusEventListener() {
    document.addEventListener('DOMContentLoaded', () => {
        toggleFieldsByWorkStatus();

        document.getElementById('id_work_status').addEventListener('change', toggleFieldsByWorkStatus);
    });
}


function toggleFieldsByLunch() {
    const lunch = document.getElementById('id_lunch');
    const show = (lunch.value == '0' || lunch.value == '1');

    toggleFieldsByName('.eat-lunch-at', show);
}

// ボタンの表示/非表示を管理
function updateButtons() {
    const workSections = Array.from(document.querySelectorAll('.work-section'));
    const lastVisibleSectionReverseIndex = workSections.slice().reverse().findIndex(s => s.style.display !== 'none');
    const lastVisibleSectionIndex = workSections.length - 1 - lastVisibleSectionReverseIndex;

    // 追加ボタン
    const addButton = document.getElementById('add-button');
    if (lastVisibleSectionIndex == workSections.length - 1) {
        addButton.disabled = true;
    } else {
        addButton.disabled = false;
    }

    // 削除ボタン
    workSections.forEach((section, index) => {
        const removeButton = section.querySelector('.remove-button');

        if (index == lastVisibleSectionIndex) {
            if (index != 0) {
                removeButton.style.display = 'inline-block';
            } else {
                removeButton.style.display = 'none';
            }
        } else {
            removeButton.style.display = 'none';
        }
    });
}

function addEventListnerToWorkSectionsButtons() {

    const workSections = Array.from(document.querySelectorAll('.work-section'));

    const addButton = document.getElementById('add-button');
    addButton.addEventListener('click', (event) => {
        const nextSection = workSections.find(s => s.style.display === 'none');
        if (nextSection) {
            toggleField(nextSection, true);// 次の勤務セクションを表示
            updateButtons();
        }
    });

    workSections.forEach(section => {
        const removeButton = section.querySelector('.remove-button');
        removeButton.addEventListener('click', (event) => {
            toggleField(section, false);
            updateButtons();
        });
    });
}

function setupToggleLunchEventListener() {
    document.addEventListener('DOMContentLoaded', () => {
        toggleFieldsByLunch();
        updateButtons();

        document.getElementById('id_lunch').addEventListener('change', toggleFieldsByLunch);
        addEventListnerToWorkSectionsButtons();
    });
}

function toggleFieldsByMorningTransport() {
    const morningTransportField = document.getElementById('id_morning_transport_means');
    const show = morningTransportField.value == '0';

    toggleFieldsByName('.pickup-fields', show);
}

function toggleFieldsByReturnTransport() {
    const morningTransportField = document.getElementById('id_return_transport_means');
    const show = morningTransportField.value == '0';

    toggleFieldsByName('.dropoff-fields', show);
}

function setupToggleTransportEventListener() {
    toggleFieldsByMorningTransport();
    toggleFieldsByReturnTransport();
    
    document.getElementById('id_morning_transport_means').addEventListener('change', toggleFieldsByMorningTransport);
    document.getElementById('id_return_transport_means').addEventListener('change', toggleFieldsByReturnTransport);    
}

// バリデーション
function validateForm(event) {
    let valid = true;
    let errorMessage = '';

    const workStatus = document.getElementById('id_work_status');

    if(workStatus && workStatus.value !== '0'){ 
        // 勤務ステータスがON or OFFICE 以外の場合（欠勤、在宅など）はチェック不要
    } else{
        const morningTransportMeans = document.getElementById('id_morning_transport_means');
        if (morningTransportMeans && morningTransportMeans.value === '0'){
            const pickupStaff = document.getElementById('id_pickup_staff');
            if(!pickupStaff.value) {
                valid = false;
                errorMessage = '送迎のスタッフの入力は必須です。'
            }
        }

        const returnTransportMeans = document.getElementById('id_return_transport_means');
        if (returnTransportMeans && returnTransportMeans.value === '0'){
            const dropoffStaff = document.getElementById('id_dropoff_staff');
            if(!dropoffStaff.value) {
                valid = false;
                errorMessage = '送迎のスタッフの入力は必須です。'
            }
        }

        // 勤務場所のチェック
        const workSections = document.querySelectorAll('.work-section');
        workSections.forEach(section => {
            if (section.style.display !== 'none') {
                const placeField = section.querySelector('select'); // 勤務場所のフィールド
                if (!placeField || !placeField.value) {
                    valid = false;
                    errorMessage = '勤務場所の入力は必須です。';
                }
            }
        });

        // 昼食の設定チェック
        const lunchField = document.getElementById('id_lunch');
        const lunchValue = lunchField.value;
        if (lunchValue === '0' || lunchValue === '1') { // 有り(注文)または有り(持参)
            const selectedLunchRadio = document.querySelector('.eat-lunch-at input[type="radio"]:checked');
            if (!selectedLunchRadio) {
                valid = false;
                errorMessage = '昼食を食べる場所を選択してください。';
            }
        }
    }

    if (!valid) {
        event.preventDefault(); // フォーム送信を中止
        alert(errorMessage); // エラーメッセージを表示
    }
}

function setupFormValidation(){
    document.addEventListener('DOMContentLoaded', () => {
        const form = document.getElementById('form');
        form.addEventListener('submit', (event) => {
            const action = event.submitter.getAttribute('value');
            if (action === 'save') {
                validateForm(event);
            }
        });
    });
}
