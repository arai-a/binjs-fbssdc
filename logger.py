class Logger:
  def __init__(self, out, parent=None):
    self.out = out
    self.parent = parent
    self.pending_comment = []
    self.count = 0
    self.enabled = True

  def enable(self):
    self.enabled = True

  def disable(self):
    self.enabled = False

  def comment(self, comment):
    if self.parent:
      self.parent.comment(comment)
      return

    if self.count != 0 and len(self.pending_comment) != 0:
      self.flush()

    self.pending_comment.append('# {}'.format(comment))

  def comment_immediate(self, comment):
    if self.parent:
      self.parent.comment_immediate(comment)
      return

    self.flush()
    self.pending_comment.append('% {}'.format(comment))
    self.flush()

  def flush(self):
    if self.parent:
      self.parent.flush()
      return

    if len(self.pending_comment) == 0 and self.count > 0:
      print()

    for comment in self.pending_comment:
      print('{} {}'.format(' ' * (32 - self.count), comment))
      self.count = 0
    self.pending_comment = []

  def print_bytes(self, b):
    if not self.enabled:
      return

    if self.parent:
      self.parent.print_bytes(b)
      return

    for c in b:
      if self.count > 3 * 8:
        print('{} \\'.format(' ' * (32 - self.count)))
        self.count = 0

      self.print_byte(c)

  def print_byte(self, c):
    print('{:02x} '.format(c), end='')
    self.count += 3

  def write(self, b):
    self.print_bytes(b)
    self.out.write(b)

  def tell(self):
    return self.out.tell()

  def getbuffer(self):
    return self.out.getbuffer()

  def close(self):
    self.flush()

  def getvalue(self):
    return self.out.getvalue()
