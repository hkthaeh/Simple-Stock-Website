window.onpopstate = function(event) {
    console.log(event.state.section);
    showSection(event.state.section);
}

function showSection(section) {
    
    fetch(`${section}`)
    .then(response => response.text())
    .then(body => {
        console.log(body);
        document.querySelector('#content').innerHTML = body;
    });
}

document.addEventListener('DOMContentLoaded', function() {

    document.querySelectorAll('li').forEach(li => {
        li.onclick = function() {

            if (!localStorage.getItem(this.dataset.page)) {
                localStorage.setItem(this.dataset.page, 0);
            };

            let counter = localStorage.getItem(this.dataset.page);
            counter ++;
            localStorage.setItem(this.dataset.page, counter);
        }
    });

    document.querySelectorAll('#psbutton').forEach(button => {
        button.onclick = function() {
            const section = this.dataset.page;
            history.pushState({section: section}, "", `${section}`);
            showSection(section);
        };
    });
});
