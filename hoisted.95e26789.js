class l extends HTMLElement{constructor(){super(),this.attachShadow({mode:"open"}),this.root=document.documentElement,this.svg}get activeEls(){return this.getAttribute("active-on")}connectedCallback(){this.setupSpark(),this.root.addEventListener("click",t=>{this.activeEls&&!t.target.matches(this.activeEls)||(this.setSparkPosition(t),this.animateSpark())})}animateSpark(){let t=[...this.svg.children],e=parseInt(t[0].getAttribute("y1")),r=e/2+"px",n=o=>{let i=`calc(${o} * (360deg / ${t.length}))`;return[{strokeDashoffset:e*3,transform:`rotate(${i}) translateY(${r})`},{strokeDashoffset:e,transform:`rotate(${i}) translateY(0)`}]},a={duration:660,easing:"cubic-bezier(0.25, 1, 0.5, 1)",fill:"forwards"};t.forEach((o,i)=>o.animate(n(i),a))}setSparkPosition(t){let e=this.root.getBoundingClientRect();this.svg.style.left=t.clientX-e.left-this.svg.clientWidth/2+"px",this.svg.style.top=t.clientY-e.top-this.svg.clientHeight/2+"px"}setupSpark(){let t=`
        <style>
          :host {
            display: contents;
          }
          
          svg {
            pointer-events: none;
            position: absolute;
            rotate: -20deg;
            stroke: var(--click-spark-color, currentcolor);
            z-index: 1000000000;
          }
  
          line {
            stroke-dasharray: 30;
            stroke-dashoffset: 30;
            transform-origin: center;
          }
        </style>
        <svg width="30" height="30" viewBox="0 0 100 100" fill="none" stroke-linecap="round" stroke-linejoin="round" stroke-width="4">
          ${Array.from({length:8},e=>'<line x1="50" y1="30" x2="50" y2="4"/>').join("")}
        </svg>
      `;this.shadowRoot.innerHTML=t,this.svg=this.shadowRoot.querySelector("svg")}}customElements.define("click-spark",l);const c=()=>document.querySelectorAll(".input-wrapper").forEach(s=>{s.addEventListener("click",t=>{s.value!==""&&s.classList.add("_filled")})});document.addEventListener("DOMContentLoaded",()=>{c()});
