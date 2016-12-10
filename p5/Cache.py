import os

class Node:
    def __init__(self, key, value):
        self.key = key
        self.value = value
        self.prev, self.next = None, None

class DoubleList:
    # initialize with dummy head and tail
    def __init__(self):
        self.head = Node(None, None)
        self.tail = Node(None, None)
        self.head.next = self.tail
        self.tail.prev = self.head
        self.size = 0                

    # insert after head
    def add(self, n):
        return self.insert(n, self.head, self.head.next)

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

class Cache:
    def __init__(self, capacity):
        self.cap = capacity
        self.items = DoubleList()
        self.mappings = {}
        self.size = 0

        # set of frequent urls that will return 404
        self.notFound = set([])
        f = open('notFound', 'r')
        lines = f.read().splitlines()
        for l in lines:
            self.notFound.add(l)
        f.close()

        # most frequent 300 urls
        self.freq = set([])
        f = open('init_300', 'r')
        lines = f.read().splitlines()
        for l in lines:
            self.freq.add(l)
        f.close()
        
        # initialize cache based on files on disk
        # for subdir, dirs, files in os.walk(os.getcwd()+'/data/'):
        #     for file in files:
        #         fname = os.path.join(subdir, file)
        #         try:
        #             f = open(fname, 'r')
        #             content = f.read()
        #             f.close()                    
        #         except:
        #             continue
        #         self.insert(fname[fname.find('/data/')+5:], content)
        #         print 'size:'+str(self.size)
        # self.print_info()
        
    def contains(self, key):
        return key in self.mappings
    
    def get(self, key):
        if key not in self.mappings: return None
        n = self.mappings[key]
        n = self.items.remove(n)
        self.items.add(n)
        return n.value

    def insert(self, key, value):
        # if val's size is too large, return false because we can't cache it
        if len(value) >= self.cap:
            return False

        if key in self.mappings:
            n = self.items.remove(self.mappings[key])
            self.size = self.size - len(n.value) + len(value)
            n.value = value
        else:
            self.size += len(value)
            self.mappings[key] = Node(key, value)        

        n = self.mappings[key]
        self.items.add(n)
        # while total size is too large, keep deleting lru item from cache            
        while self.size >= self.cap:
            n = self.items.removeLast()
            self.size -= len(n.value)
            del self.mappings[n.key]
    
        # self.print_info()
        return True

    def _pathToFile(self, path):
        if path == '/':
            return os.getcwd() + '/data/Main_Page'
        else:
            return os.getcwd() + '/data' + path
        
    def print_info(self):
        n = self.items.head.next
        while n.key is not None:
            print '[' + str(n.key) +', ' + "" + '], ',
            n = n.next
        print 'number of keys: ' + str(len(self.mappings)) + ', ',
        print 'total size: ' + str(self.size)
    
if __name__ == '__main__':
    cache = Cache(5)
    cache.insert('a/b/c','x')
    cache.insert('k/d','y')
    cache.print_info()
    cache.get('a/b/c')
    cache.print_info()
    cache.get('k/d')
    cache.print_info()
    cache.insert('a/b/e','z')
    cache.insert('k/qq','a')
    cache.print_info()        
    cache.insert('k/qq','abc')
    cache.print_info()
    cache.insert('pp','k')
    cache.print_info()    
    
