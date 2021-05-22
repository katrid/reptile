namespace Reptile {
  export class ReportContainer {
    pages: Page[] = [];
    pageFooter: Band;

    constructor(public el: HTMLElement, public template: HTMLElement) {
    }

    prepare() {
      // find page footer
      let pageFooter = new Band(this.template.querySelector('.page-footer'));
      pageFooter.el.parentElement.removeChild(pageFooter.el);
      this.pageFooter = pageFooter;

      let page = this.currentPage;
      for (let child of Array.from(this.template.children)) {
        page = this.prepareElement(child as HTMLElement, page);
      }
      for (page of this.pages) {
        page.end();
        this.el.append(page.el);
      }
    }

    prepareElement(el: HTMLElement, page: Page): Page {
      if (page.checkRect(el))
        page.append(el);
      else {
        console.log('crop elements')
        let crop = new Crop(el, page);
        page = crop.page;
      }
      return page;
    }

    splitElement(el: HTMLElement, page: Page) {
      let clone = document.createElement(el.tagName);
      clone.classList.add(...el.classList);
      for (let child of el.children) {
        if (page.checkRect(child as HTMLElement))
          clone.append(child);
      }
      return clone;
    }

    get currentPage() {
      if (!this.pages.length)
        return this.newPage();
    }

    newPage() {
      let page = new Page(this);
      page.pageFooter = this.pageFooter;
      this.pages.push(page);
      return page;
    }
  }

  class Page {
    el: HTMLElement;
    ay: number;
    objects: HTMLElement[] = [];
    private _pageFooter: Band;

    constructor(public container: ReportContainer) {
      this.el = document.createElement('div');
      this.el.classList.add('reptile-page', 'A4');
      document.body.append(this.el);
      this.ay = this.el.clientHeight;
    }

    get pageFooter() {
      return this._pageFooter;
    }

    set pageFooter(footer) {
      this._pageFooter = footer;
      if (footer) {
        this.ay -= footer.height;
        let el = footer.clone();
        this.el.appendChild(el);
      }
    }

    append(child: HTMLElement) {
      this.objects.push(child);
    }

    checkRect(child: HTMLElement) {
      let rect = child.getBoundingClientRect();
      return rect.bottom <= this.ay;
    }

    end() {
      for (let obj of this.objects) {
        if (obj instanceof Crop) {}
        else {
          this.el.appendChild(obj);
        }

      }
    }
  }

  class Crop {
    el: HTMLElement;
    objects: any[] = [];
    next: Crop;

    constructor(public container: HTMLElement, public page: Page, public parent: Crop=null) {
      // clone the container
      this.el = document.createElement(container.tagName);
      for (let child of container.children) {
        if (page.checkRect(child as HTMLElement))
          this.objects.push(child as HTMLElement);
        else if (child.classList.contains('band'))  // band is indivisible (for while)
          this.forceNewPage();
        else
          this.objects.push(new Crop(child as HTMLElement, page));
      }
    }

    forceNewPage() {
      let page = this.page.container.newPage();
      let parent = this.parent;
      // move parent crop to the new page
      while (parent) {
        parent.page = page;
        parent = parent.parent;
      }
      this.page = page;
      return page;
    }

    clone(container: HTMLElement) {
      let el  = document.createElement(container.tagName);
      el.classList.add(...container.classList);
      return el;
    }
  }


  class Band {
    height: number;

    constructor(public el: HTMLElement) {
      this.height = el.clientHeight;
    }

    clone(): HTMLElement {
      let el = document.createElement('div');
      el.innerHTML = this.el.outerHTML;
      return el.firstChild as HTMLElement;
    }
  }

}
