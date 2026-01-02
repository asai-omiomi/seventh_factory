function toggleFieldsByName(selector, show, parent=document) {

    const targetFields = parent.querySelectorAll(selector);
    if (!targetFields) return;
    _toggleFields(targetFields, show);
}

function _toggleFields(targetFields, show) {
    targetFields.forEach(field => {
        _toggleField(field, show);
    });
}

function _toggleField(field, show) {
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

function _toggleFieldsByWorkStatus() {
    const elements = document.querySelectorAll('.work-status');

    elements.forEach(el => {
        const show = el.value === '1'; // '1' と文字列比較
        // 親要素の .work-fields 内だけを切り替え
        const parent = el.closest('.work-fields');
        if (parent) {
            toggleFieldsByName('.toggle-fields', show, parent);
        }
    });
}

function setupToggleWorkStatusControl() {
    document.addEventListener('DOMContentLoaded', () => {

        _toggleFieldsByWorkStatus();

        const elements = document.querySelectorAll('.work-status');
        elements.forEach(el => {
            el.addEventListener('change', _toggleFieldsByWorkStatus);
        });
    });
}

function _toggleTransferDetails(type, className) {
    const select = document.querySelector(`.${type}`);
    if (!select) return;

    const show = select.value == TRANSFER_VALUE;
    toggleFieldsByName(`.${className}`, show);
}

// 初期化とイベント設定
function setupTransportControl() {
    document.addEventListener('DOMContentLoaded', () => {
        ['morning', 'return'].forEach(type => {
            const className = type === 'morning' ? 'morning_transfer_details' : 'return_transfer_details';
            const select = document.querySelector(`.${type}`);
            if (!select) return;

            select.addEventListener('change', () => _toggleTransferDetails(type, className));

            // 初期表示の設定
            _toggleTransferDetails(type, className);
        });
    });
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
        if (morningTransportMeans && morningTransportMeans.value === TRANSFER_VALUE){
            const pickupStaff = document.getElementById('id_pickup_staff');
            if(!pickupStaff.value) {
                valid = false;
                errorMessage = '送迎のスタッフの入力は必須です。'
            }
        }

        const returnTransportMeans = document.getElementById('id_return_transport_means');
        if (returnTransportMeans && returnTransportMeans.value === TRANSFER_VALUE){
            const dropoffStaff = document.getElementById('id_dropoff_staff');
            if(!dropoffStaff.value) {
                valid = false;
                errorMessage = '送迎のスタッフの入力は必須です。'
            }
        }

        // 勤務場所のチェック
        // const workSections = document.querySelectorAll('.work-section');
        // workSections.forEach(section => {
        //     if (section.style.display !== 'none') {
        //         const placeField = section.querySelector('select'); // 勤務場所のフィールド
        //         if (!placeField || !placeField.value) {
        //             valid = false;
        //             errorMessage = '勤務場所の入力は必須です。';
        //         }
        //     }
        // });
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
