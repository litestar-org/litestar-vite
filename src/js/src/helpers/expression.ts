type ExpressionContext = Record<string, unknown>

type TemplateToken = {
  expressions: string[]
  strings: string[]
}

type Token = { kind: "ident" | "num" | "punct" | "str"; value: string } | { kind: "template"; template: TemplateToken }

type Node =
  | { type: "Literal"; value: unknown }
  | { type: "Ident"; name: string }
  | { type: "Member"; object: Node; name: string }
  | { type: "Call"; callee: Node; args: Node[] }
  | { type: "Unary"; operator: string; value: Node }
  | { type: "Binary"; operator: string; left: Node; right: Node }
  | { type: "Ternary"; condition: Node; yes: Node; no: Node }
  | { type: "Object"; entries: Array<[string, Node]> }
  | { type: "Template"; strings: string[]; expressions: Node[] }

const ALLOWED_GLOBALS: Readonly<Record<string, unknown>> = Object.freeze({ JSON, Math })
const STOP_PROTOS: ReadonlySet<unknown> = new Set([Object.prototype, Array.prototype, Function.prototype, String.prototype, Number.prototype, Boolean.prototype])
const BANNED_PROPS = new Set([
  "constructor",
  "__proto__",
  "prototype",
  "__defineGetter__",
  "__defineSetter__",
  "__lookupGetter__",
  "__lookupSetter__",
  "caller",
  "callee",
  "arguments",
  "apply",
  "call",
  "bind",
])
const RESERVED = new Set(["function", "this", "new", "import", "delete", "void", "typeof", "instanceof", "in", "class", "return", "var", "let", "const", "async", "await", "yield"])
const BINARY_PRECEDENCE: Readonly<Record<string, number>> = Object.freeze({
  "??": 1,
  "||": 2,
  "&&": 3,
  "==": 4,
  "!=": 4,
  "===": 4,
  "!==": 4,
  "<": 5,
  "<=": 5,
  ">": 5,
  ">=": 5,
  "+": 6,
  "-": 6,
  "*": 7,
  "/": 7,
  "%": 7,
})
const PUNCTUATION = ["===", "!==", "&&", "||", "??", "<=", ">=", "==", "!=", ".", "(", ")", "{", "}", ",", "?", ":", "!", "+", "-", "*", "/", "%", "<", ">"]

function readEscape(source: string, start: number): { end: number; value: string } | null {
  const character = source[start]
  if (character === undefined) return null
  if (character === "u") {
    if (source[start + 1] === "{") {
      const close = source.indexOf("}", start + 2)
      if (close === -1) return null
      const digits = source.slice(start + 2, close)
      if (!/^[0-9a-f]+$/i.test(digits)) return null
      const codePoint = Number.parseInt(digits, 16)
      if (!Number.isFinite(codePoint) || codePoint > 0x10ffff) return null
      return { end: close + 1, value: String.fromCodePoint(codePoint) }
    }
    const digits = source.slice(start + 1, start + 5)
    if (!/^[0-9a-f]{4}$/i.test(digits)) return null
    return { end: start + 5, value: String.fromCharCode(Number.parseInt(digits, 16)) }
  }
  if (character === "x") {
    const digits = source.slice(start + 1, start + 3)
    if (!/^[0-9a-f]{2}$/i.test(digits)) return null
    return { end: start + 3, value: String.fromCharCode(Number.parseInt(digits, 16)) }
  }
  const escapes: Readonly<Record<string, string>> = {
    b: "\b",
    f: "\f",
    n: "\n",
    r: "\r",
    t: "\t",
    v: "\v",
  }
  return { end: start + 1, value: escapes[character] ?? character }
}

function readString(source: string, start: number): { end: number; value: string } | null {
  const quote = source[start]
  if (quote !== "'" && quote !== '"') return null
  let value = ""
  for (let index = start + 1; index < source.length; index += 1) {
    const character = source[index]
    if (character === quote) return { end: index + 1, value }
    if (character === "\\") {
      const escaped = readEscape(source, index + 1)
      if (!escaped) return null
      value += escaped.value
      index = escaped.end - 1
      continue
    }
    if (character === "\n" || character === "\r") return null
    value += character
  }
  return null
}

function findTemplateExpressionEnd(source: string, start: number): number | null {
  let depth = 1
  for (let index = start; index < source.length; index += 1) {
    const character = source[index]
    if (character === "'" || character === '"') {
      const quoted = readString(source, index)
      if (!quoted) return null
      index = quoted.end - 1
      continue
    }
    if (character === "`") {
      const nested = readTemplate(source, index)
      if (!nested) return null
      index = nested.end - 1
      continue
    }
    if (character === "{") depth += 1
    if (character === "}") {
      depth -= 1
      if (depth === 0) return index
    }
  }
  return null
}

function readTemplate(source: string, start: number): { end: number; template: TemplateToken } | null {
  if (source[start] !== "`") return null
  const strings: string[] = []
  const expressions: string[] = []
  let value = ""
  for (let index = start + 1; index < source.length; index += 1) {
    const character = source[index]
    if (character === "\\") {
      const escaped = readEscape(source, index + 1)
      if (!escaped) return null
      value += escaped.value
      index = escaped.end - 1
      continue
    }
    if (character === "`") {
      strings.push(value)
      return { end: index + 1, template: { expressions, strings } }
    }
    if (character === "$" && source[index + 1] === "{") {
      strings.push(value)
      value = ""
      const close = findTemplateExpressionEnd(source, index + 2)
      if (close === null) return null
      expressions.push(source.slice(index + 2, close))
      index = close
      continue
    }
    value += character
  }
  return null
}

function isIdentifierStart(character: string | undefined): boolean {
  return character !== undefined && /[A-Za-z_$]/.test(character)
}

function isIdentifierPart(character: string | undefined): boolean {
  return character !== undefined && /[A-Za-z0-9_$]/.test(character)
}

function tokenize(source: string): Token[] | null {
  const tokens: Token[] = []
  for (let index = 0; index < source.length; ) {
    const character = source[index]
    if (/\s/.test(character)) {
      index += 1
      continue
    }
    if (character === "'" || character === '"') {
      const quoted = readString(source, index)
      if (!quoted) return null
      tokens.push({ kind: "str", value: quoted.value })
      index = quoted.end
      continue
    }
    if (character === "`") {
      const template = readTemplate(source, index)
      if (!template) return null
      tokens.push({ kind: "template", template: template.template })
      index = template.end
      continue
    }
    if (/\d/.test(character)) {
      const match = source.slice(index).match(/^(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?/i)
      if (!match) return null
      tokens.push({ kind: "num", value: match[0] })
      index += match[0].length
      continue
    }
    if (isIdentifierStart(character)) {
      let end = index + 1
      while (isIdentifierPart(source[end])) end += 1
      tokens.push({ kind: "ident", value: source.slice(index, end) })
      index = end
      continue
    }
    if (character === "[" || character === "]" || source.startsWith("=>", index)) return null
    if (source.startsWith("//", index) || source.startsWith("/*", index)) return null
    const punctuation = PUNCTUATION.find((candidate) => source.startsWith(candidate, index))
    if (!punctuation) return null
    tokens.push({ kind: "punct", value: punctuation })
    index += punctuation.length
  }
  return tokens
}

class Parser {
  private index = 0

  constructor(private readonly tokens: Token[]) {}

  parse(): Node | null {
    const node = this.parseExpression()
    return node && this.index === this.tokens.length ? node : null
  }

  private peek(): Token | undefined {
    return this.tokens[this.index]
  }

  private takePunctuation(value: string): boolean {
    const token = this.peek()
    if (token?.kind !== "punct" || token.value !== value) return false
    this.index += 1
    return true
  }

  private parseExpression(minimumPrecedence = 0): Node | null {
    let left = this.parseUnary()
    if (!left) return null
    while (true) {
      const token = this.peek()
      if (token?.kind !== "punct") break
      const precedence = BINARY_PRECEDENCE[token.value]
      if (precedence === undefined || precedence < minimumPrecedence) break
      this.index += 1
      const right = this.parseExpression(precedence + 1)
      if (!right) return null
      left = { type: "Binary", operator: token.value, left, right }
    }
    if (minimumPrecedence === 0 && this.takePunctuation("?")) {
      const yes = this.parseExpression()
      if (!yes || !this.takePunctuation(":")) return null
      const no = this.parseExpression()
      if (!no) return null
      left = { type: "Ternary", condition: left, yes, no }
    }
    return left
  }

  private parseUnary(): Node | null {
    const token = this.peek()
    if (token?.kind === "punct" && (token.value === "!" || token.value === "+" || token.value === "-")) {
      this.index += 1
      const value = this.parseUnary()
      return value ? { type: "Unary", operator: token.value, value } : null
    }
    return this.parsePostfix()
  }

  private parsePostfix(): Node | null {
    let node = this.parsePrimary()
    if (!node) return null
    while (true) {
      if (this.takePunctuation(".")) {
        const property = this.peek()
        if (property?.kind !== "ident" || BANNED_PROPS.has(property.value) || RESERVED.has(property.value)) {
          return null
        }
        this.index += 1
        node = { type: "Member", object: node, name: property.value }
        continue
      }
      if (this.takePunctuation("(")) {
        const args: Node[] = []
        if (!this.takePunctuation(")")) {
          while (true) {
            const argument = this.parseExpression()
            if (!argument) return null
            args.push(argument)
            if (this.takePunctuation(")")) break
            if (!this.takePunctuation(",")) return null
          }
        }
        node = { type: "Call", callee: node, args }
        continue
      }
      return node
    }
  }

  private parsePrimary(): Node | null {
    const token = this.peek()
    if (!token) return null
    if (token.kind === "num") {
      this.index += 1
      return { type: "Literal", value: Number(token.value) }
    }
    if (token.kind === "str") {
      this.index += 1
      return { type: "Literal", value: token.value }
    }
    if (token.kind === "template") {
      this.index += 1
      const expressions: Node[] = []
      for (const source of token.template.expressions) {
        const expression = parseSource(source)
        if (!expression) return null
        expressions.push(expression)
      }
      return { type: "Template", strings: token.template.strings, expressions }
    }
    if (token.kind === "ident") {
      this.index += 1
      if (token.value === "true") return { type: "Literal", value: true }
      if (token.value === "false") return { type: "Literal", value: false }
      if (token.value === "null") return { type: "Literal", value: null }
      if (token.value === "undefined") return { type: "Literal", value: undefined }
      if (RESERVED.has(token.value) || BANNED_PROPS.has(token.value)) return null
      return { type: "Ident", name: token.value }
    }
    if (this.takePunctuation("(")) {
      const expression = this.parseExpression()
      return expression && this.takePunctuation(")") ? expression : null
    }
    if (this.takePunctuation("{")) return this.parseObject()
    return null
  }

  private parseObject(): Node | null {
    const entries: Array<[string, Node]> = []
    if (this.takePunctuation("}")) return { type: "Object", entries }
    while (true) {
      const keyToken = this.peek()
      if (!keyToken || (keyToken.kind !== "ident" && keyToken.kind !== "str")) return null
      const key = keyToken.value
      if (BANNED_PROPS.has(key)) return null
      this.index += 1
      if (!this.takePunctuation(":")) return null
      const value = this.parseExpression()
      if (!value) return null
      entries.push([key, value])
      if (this.takePunctuation("}")) return { type: "Object", entries }
      if (!this.takePunctuation(",")) return null
    }
  }
}

function parseSource(source: string): Node | null {
  const tokens = tokenize(source)
  return tokens ? new Parser(tokens).parse() : null
}

function resolveIdent(name: string, context: ExpressionContext): unknown {
  let object: unknown = context
  while (object !== null && object !== undefined && !STOP_PROTOS.has(object)) {
    if (Object.prototype.hasOwnProperty.call(object, name)) {
      return (object as Record<string, unknown>)[name]
    }
    object = Object.getPrototypeOf(object)
  }
  return Object.prototype.hasOwnProperty.call(ALLOWED_GLOBALS, name) ? ALLOWED_GLOBALS[name] : undefined
}

function isPlainReceiver(value: unknown): boolean {
  const valueType = typeof value
  if (valueType === "string" || valueType === "number" || valueType === "boolean" || valueType === "function") {
    return true
  }
  if (value === null || valueType !== "object") return false
  const firstPrototype = Object.getPrototypeOf(value)
  if (firstPrototype === null || STOP_PROTOS.has(firstPrototype)) return true
  const secondPrototype = Object.getPrototypeOf(firstPrototype)
  return secondPrototype === null || STOP_PROTOS.has(secondPrototype)
}

function readMember(object: unknown, name: string): unknown {
  if (object === null || object === undefined || !isPlainReceiver(object)) return undefined
  return (object as Record<string, unknown>)[name]
}

function add(left: unknown, right: unknown): unknown {
  if (typeof left === "string" || typeof right === "string") return String(left) + String(right)
  return Number(left) + Number(right)
}

function looselyEqual(left: unknown, right: unknown): boolean {
  if (left === right) return true
  if (left == null && right == null) return true
  if (typeof left === "boolean" || typeof right === "boolean") return Number(left) === Number(right)
  if ((typeof left === "number" && typeof right === "string") || (typeof left === "string" && typeof right === "number")) {
    return Number(left) === Number(right)
  }
  return false
}

function compare(left: unknown, right: unknown, operator: string): boolean {
  const comparableLeft = typeof left === "string" && typeof right === "string" ? left : Number(left)
  const comparableRight = typeof left === "string" && typeof right === "string" ? right : Number(right)
  if (operator === "<") return comparableLeft < comparableRight
  if (operator === "<=") return comparableLeft <= comparableRight
  if (operator === ">") return comparableLeft > comparableRight
  return comparableLeft >= comparableRight
}

function evaluateBinary(node: Extract<Node, { type: "Binary" }>, context: ExpressionContext): unknown {
  const left = evaluate(node.left, context)
  if (node.operator === "&&") return left ? evaluate(node.right, context) : left
  if (node.operator === "||") return left ? left : evaluate(node.right, context)
  if (node.operator === "??") return left === null || left === undefined ? evaluate(node.right, context) : left
  const right = evaluate(node.right, context)
  if (node.operator === "+") return add(left, right)
  if (node.operator === "-") return Number(left) - Number(right)
  if (node.operator === "*") return Number(left) * Number(right)
  if (node.operator === "/") return Number(left) / Number(right)
  if (node.operator === "%") return Number(left) % Number(right)
  if (node.operator === "===") return left === right
  if (node.operator === "!==") return left !== right
  if (node.operator === "==") return looselyEqual(left, right)
  if (node.operator === "!=") return !looselyEqual(left, right)
  return compare(left, right, node.operator)
}

function evaluate(node: Node, context: ExpressionContext): unknown {
  if (node.type === "Literal") return node.value
  if (node.type === "Ident") return resolveIdent(node.name, context)
  if (node.type === "Member") return readMember(evaluate(node.object, context), node.name)
  if (node.type === "Call") {
    const args = node.args.map((argument) => evaluate(argument, context))
    if (node.callee.type === "Member") {
      const receiver = evaluate(node.callee.object, context)
      const callable = readMember(receiver, node.callee.name)
      return typeof callable === "function" ? Reflect.apply(callable, receiver, args) : undefined
    }
    const callable = evaluate(node.callee, context)
    return typeof callable === "function" ? Reflect.apply(callable, undefined, args) : undefined
  }
  if (node.type === "Unary") {
    const value = evaluate(node.value, context)
    if (node.operator === "!") return !value
    if (node.operator === "-") return -Number(value)
    return Number(value)
  }
  if (node.type === "Binary") return evaluateBinary(node, context)
  if (node.type === "Ternary") {
    return evaluate(node.condition, context) ? evaluate(node.yes, context) : evaluate(node.no, context)
  }
  if (node.type === "Object") {
    const result: Record<string, unknown> = {}
    for (const [key, value] of node.entries) result[key] = evaluate(value, context)
    return result
  }
  let result = node.strings[0] ?? ""
  for (let index = 0; index < node.expressions.length; index += 1) {
    result += String(evaluate(node.expressions[index], context))
    result += node.strings[index + 1] ?? ""
  }
  return result
}

export function compileExpression(source: string): ((context: ExpressionContext) => unknown) | null {
  const syntaxTree = parseSource(source)
  if (!syntaxTree) return null
  return (context) => {
    try {
      return evaluate(syntaxTree, context)
    } catch {
      return undefined
    }
  }
}
