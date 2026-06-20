# LaTeX Test File / LaTeX 測試文件

## Basic Markdown（基本格式）

**Bold text** / *Italic text* / ~~Strikethrough~~ / `inline code`

- List item one
- List item two

> Blockquote example





Inline LaTeX（行內公式）

Einstein's famous equation: $E = mc^2$

Inline LaTeX（行內公式）

Einstein's famous equation: $E = mc^2$



Inline LaTeX（行內公式）

Einstein's famous equation: $E = mc^2$

---

## Inline LaTeX（行內公式）

Einstein's famous equation: $E = mc^2$

The quadratic formula: $x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}$

Pythagorean theorem: $a^2 + b^2 = c^2$

Euler's identity: $e^{i\pi} + 1 = 0$

Derivative: $\frac{d}{dx}e^x = e^x$

---

## Display LaTeX（獨立公式）

The Gaussian integral:

$$\int_{-\infty}^{\infty} e^{-x^2} dx = \sqrt{\pi}$$

Taylor series:

$$e^x = \sum_{n=0}^{\infty} \frac{x^n}{n!}$$

Schrödinger equation:

$$i\hbar\frac{\partial}{\partial t}|\Psi\rangle = \hat{H}|\Psi\rangle$$

Maxwell's equations:

$$\nabla \cdot \vec{E} = \frac{\rho}{\epsilon_0}$$

$$\nabla \times \vec{E} = -\frac{\partial\vec{B}}{\partial t}$$

---

## Mixed Content（混合內容）

The **Black-Scholes** model uses the formula:

$$C(S,t) = SN(d_1) - Ke^{-r(T-t)}N(d_2)$$

where:

$$d_1 = \frac{\ln(S/K) + (r + \sigma^2/2)(T-t)}{\sigma\sqrt{T-t}}$$
$$d_2 = d_1 - \sigma\sqrt{T-t}$$

And the heat equation: $\frac{\partial u}{\partial t} = \alpha \nabla^2 u$

---

## Code Block（程式碼）

```python
def hello():
    print("LaTeX test complete! ✅")
```
