class Node:
    def __init__(self, item):
        self.item = item
        self.prev, self.next = None, None

class DoubleList:
    # initialize with dummy head and tail
    def __init__(self):
        self.head = Node(None)
        self.tail = Node(None)
        self.head.next = self.tail
        self.tail.prev = self.head
        self.size = 0

    # insert before dummy tail
    def add(self, n):
        return self.insert(n, self.tail.prev, self.tail)

    # insert a node n between prev and next
    def insert(self, n, prev, next):
        n.next = next
        n.prev = prev
        prev.next = n
        next.prev = n
        self.size += 1
        return n

    # remove last node
    def removeLast(self):
        return self.remove(self.tail.prev)

    # remove node n
    def remove(self, n):
        if n is self.head or n is self.tail:
            return None
        n.prev.next = n.next
        n.next.prev = n.prev
        self.size -= 1
        return n

# a frequency node, self.item(freq) is the frequency, self.itemsList is the
# list of all the items that has the frequency freq
class FreqNode(Node):
    def __init__(self, freq):
        Node.__init__(self, freq)
        self.itemsList = DoubleList()

    # append a new node
    def add(self, n):
        self.itemsList.add(n)

    # remvoe a node n
    def remove(self, n):
        return self.itemsList.remove(n)
    
    # remove last node
    def removeLast(self):
        return self.itemsList.removeLast()

# Cache maps key to the LfuItem
# self.parent is the its FreqNode, self.node is corresponding node with that key,
# self.item is the value corresponding to that key
class LfuItem:
    def __init__(self, parent, n, value):
        self.parent = parent
        self.node = n
        self.value = value

# cache.mappings maps key to a LfuItem, cache.freqList is a list of FreqNode
class Cache:
    def __init__(self, capacity):
        self.capacity = capacity
        self.mappings = {}
        self.freqList = DoubleList()

    # whether cache has the key
    def containsKey(self, key):
        return key in self.mappings

    # insert a (key, val) to cache with frequency = 1
    def insert(self, key, val):
        if key in self.mappings:
            return False
        first = self.freqList.head.next
        # If the smallest frequency in cache is not 1, then make new FreqNode with 1
        if first.item != 1:
            freqOfOne = FreqNode(1)
            first = self.freqList.insert(freqOfOne, self.freqList.head, first)
        # add the node to FreqNode, self.mappings
        node = Node(key)
        first.add(node)
        self.mappings[key] = LfuItem(first, node, val)
        return True

    # access the value correspnding to key
    def access(self, key):
        if key not in self.mappings:
            return None
        parent, node, item = self.mappings[key].parent, self.mappings[key].node, self.mappings[key].value
        parent_next = parent.next
        # increase frequency by 1
        if parent_next.item != parent.item + 1:
            inc = FreqNode(parent.item + 1)
            parent_next = self.freqList.insert(inc, parent, parent_next)
        # remove the node under old frequency, add it to new FreqNode
        parent.remove(node)
        parent_next.add(node)
        self.mappings[key].parent = parent_next
        # if no node left under old frequency, delete theat FreqNode
        if parent.itemsList.size == 0:
            self.freqList.remove(parent)
        return item

    # remove the least frequent node
    def remove(self):
        first = self.freqList.head.next
        if first.item is None: return
        tmp = first.removeLast()
        # if no node left under old frequency, delete theat FreqNode
        if first.itemsList.size == 0:
            self.freqList.remove(first)
        del self.mappings[tmp.item]

    def print_info(self):
        n = self.freqList.head.next
        while n.item is not None:
            print str(n.item) + ': ',
            i = n.itemsList.head.next
            while i.item is not None:
                print i.item, self.mappings[i.item].value,
                i = i.next
            n = n.next
            print

if __name__ == '__main__':
    cache = Cache(100)
    cache.insert(1,'x')
    cache.insert(2,'y')
    cache.print_info()
    print cache.access(1)
    cache.print_info()
    print cache.access(2)
    print cache.access(2)    
    cache.print_info()
