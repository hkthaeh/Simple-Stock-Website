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
});
