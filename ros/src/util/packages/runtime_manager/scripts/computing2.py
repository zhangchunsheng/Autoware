#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""Autoware2 Computing Tab Prototype."""

"""
  Copyright (c) 2015, Nagoya University
  All rights reserved.

  Redistribution and use in source and binary forms, with or without
  modification, are permitted provided that the following conditions are met:

  * Redistributions of source code must retain the above copyright notice, this
    list of conditions and the following disclaimer.

  * Redistributions in binary form must reproduce the above copyright notice,
    this list of conditions and the following disclaimer in the documentation
    and/or other materials provided with the distribution.

  * Neither the name of Autoware nor the names of its
    contributors may be used to endorse or promote products derived from
    this software without specific prior written permission.

  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
  AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
  IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
  DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
  FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
  DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
  SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
  CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
  OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
  OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import sys
import os
import wx
import subprocess
import xml.etree.ElementTree as XMLET

class ComputingConfig():
  """Parse computing.xml."""
  def __init__(self, fname):
    self.packages_ = []
    #if not os.path.exists(fname):
    #  return
    try:
      tree = XMLET.parse(fname)
    except XMLET.ParseError:
      print >> sys.stderr, "%s: parse error" % (fname)
      return
    root = tree.getroot()
    for grp in root:
      if grp.tag != "group":
        print >> sys.stderr, "%s: \"%s\" is not group, skipping" % (fname, grp.tag)
        continue
      v = {}
      for elem in grp:
        v[elem.tag] = elem.text
      if not 'name' in v:
        print >> sys.stderr, "%s: no name" % (fname)
        continue
      if not 'path' in v:
        print >> sys.stderr, "%s: no path" % (fname)
        continue
      pkgpath = os.path.join('src', v['path'], 'packages')
      self.packages_.append((v['name'], \
        [d for d in os.listdir(pkgpath) if os.path.isdir(os.path.join(pkgpath, d))]))

  def getNames(self):
    """Returns category names."""
    return map(lambda n:n[0], self.packages_)

  def getPackages(self, name):
    """Returns package names."""
    for v in self.packages_:
      if v[0] == name:
        return v[1]
    return []

class PackageConfig():
  """Parse interface.xml."""

  class NodeGroup():
    """Node group."""
    def __init__(self, node, iset, oset):
      self.nodes_ = [node]
      self.iset_ = iset
      self.oset_ = oset
      self.label_ = self.getLabel0()
      self.togrp_ = []
      self.frgrp_ = []
    def addNode(self, node):
      self.nodes_.append(node)
    def getNodes(self):
      return self.nodes_
    def getLabel0(self):
      """Creates unique label by topics."""
      istr = reduce(lambda m,n:m+';'+n, sorted(self.iset_)) \
        if len(self.iset_) > 0 else ''
      ostr = reduce(lambda m,n:m+';'+n, sorted(self.oset_)) \
        if len(self.oset_) > 0 else ''
      return istr + ';' + ostr
    def getLabel(self):
      """Returns label."""
      return self.label_
    def getInTopics(self):
      """Returns subscribed topics."""
      return self.iset_
    def getOutTopics(self):
      """Returns published topics."""
      return self.oset_
    def addFromGroup(self, label):
      self.frgrp_.append(label)
    def getFromGroups(self):
      return self.frgrp_
    def addToGroup(self, label):
      self.togrp_.append(label)
    def getToGroups(self):
      return self.togrp_

  def __init__(self, fname):
    self.namespaces_ = []
    self.groups_ = {}
    if not os.path.exists(fname):
      return
    try:
      tree = XMLET.parse(fname)
    except XMLET.ParseError:
      print >> sys.stderr, "%s: parse error" % (fname)
      return
    root = tree.getroot()
    for grp in root:
      if grp.tag == "namespaces":
        for ns in grp:
          if ns.tag == "namespace":
            self.namespaces_.append(ns.text)
      if grp.tag == "nodes":
        for node in grp:
          if node.tag != "node":
            continue
          name = ''
          iset = set()
          oset = set()
          for elem in node:
            if elem.tag == "name":
              name = elem.text
            if elem.tag == "in":
              iset.update([elem.text])
            if elem.tag == "out":
              oset.update([elem.text])
          if len(name) > 0:
            grp = self.NodeGroup(name, iset, oset)
            label = grp.getLabel()
            if label in self.groups_:
              self.groups_[label].addNode(name)
            else:
              self.groups_[label] = grp
          else:
            print >> sys.stderr, "%s: no name" % (fname)

    labels1 = self.groups_.keys()
    labels2 = self.groups_.keys()
    for l1 in labels1:
      labels2.remove(l1)
      for l2 in labels2:
        c = self.compareNode(l1, l2)
        if c > 0:
          self.groups_[l1].addToGroup(l2)
          self.groups_[l2].addFromGroup(l1)
        elif c < 0:
          self.groups_[l2].addToGroup(l1)
          self.groups_[l1].addFromGroup(l2)

  def isEmpty(self):
    return (len(self.nodes_) == 0)

  def getNamespaces(self):
    """Returns namespace names."""
    return self.namespaces_

  def getLabel(self, node):
    """Returns the label of the node."""
    for label in self.groups_.keys():
      if node in self.groups_[label].getNodes():
        return label
    return None

  def getSameNodes(self, name):
    """Returns nodes of the same group."""
    label = self.getLabel(name)
    return self.getNodesByLabel(label)

  def getInTopics(self, node):
    """Returns subscribed topics of the node."""
    for label in self.groups_.keys():
      if node in self.groups_[label].getNodes():
        return self.groups_[label].getInTopics()
    return []

  def getOutTopics(self, node):
    """Returns published topics of the node."""
    for label in self.groups_.keys():
      if node in self.groups_[label].getNodes():
        return self.groups_[label].getOutTopics()
    return []

  def getNodesByLabel(self, label):
    """Returns nodes of the label."""
    if label in self.groups_:
      return self.groups_[label].getNodes()
    else:
      return []

  def getLabelsByLevel(self, n):
    labels = []
    for label in self.groups_.keys():
      if len(self.groups_[label].getFromGroups()) <= 0:
        labels.append(label)
    for i in range(0, n):
      nlabels = []
      for label in labels:
        nlabels.extend(self.groups_[label].getToGroups())
      labels = nlabels
    return set(labels)

  def compareNode(self, label1, label2):
    """Compare nodes."""
    topics2 = self.groups_[label2].getOutTopics()
    for t1 in self.groups_[label1].getInTopics():
      if t1 in topics2:
        return -1
    topics1 = self.groups_[label1].getOutTopics()
    for t2 in self.groups_[label2].getInTopics():
      if t2 in topics1:
        return 1
    return 0

class PackageDialog(wx.Dialog):
  """Package dialog."""
  def __init__(self, parent, id, title):
    wx.Dialog.__init__(self, parent, id, title);
    self.panel_ = wx.Panel(self, -1)
    vbox = wx.BoxSizer(wx.VERTICAL)
    self.conf_ = PackageConfig(self.GetPackageXML(title))
    self.panels_ = {}

    hpanel = wx.Panel(self.panel_, -1)
    hbox = wx.BoxSizer(wx.HORIZONTAL)
    hpanel.SetSizer(hbox)
    i = 0
    labels = self.conf_.getLabelsByLevel(i)
    while len(labels) > 0:
      subpanel = wx.Panel(hpanel, -1)
      subbox = wx.BoxSizer(wx.VERTICAL)
      subpanel.SetSizer(subbox)
      for label in labels:
        grppanel = wx.Panel(subpanel, -1)
        grpbox = wx.StaticBoxSizer(wx.StaticBox(grppanel, -1, ""), orient=wx.VERTICAL)
        grppanel.SetSizer(grpbox)
        self.panels_[label] = {'panel':grppanel, 'x':0, 'y':0}
        for node in self.conf_.getNodesByLabel(label):
          self.addNode(node, grppanel, grpbox)
        subbox.Add(grppanel, flag=wx.ALL, border=2)
      hbox.Add(subpanel, flag=wx.ALL|wx.ALIGN_CENTER_VERTICAL, border=1)
      i += 1
      labels = self.conf_.getLabelsByLevel(i)
      if len(labels) > 0:
        hbox.Add(wx.StaticText(hpanel, -1, ""), 
          flag=wx.ALL|wx.ALIGN_CENTER_VERTICAL, border=32)

    vbox.Add(hpanel, flag=wx.ALL, border=2)

    self.addButtons(self.panel_, vbox)
    self.panel_.SetSizer(vbox)

    self.SetSize(self.panel_.GetBestSize())
    self.Centre()
    self.Show(True)
    self.SetPanelsXY()

  def GetPackageXML(self, name):
    try:
      path = subprocess.check_output(['rospack', 'find', name]).strip()
    except subprocess.CalledProcessError:
      path = '.'
    return os.path.join(path, 'interface.xml')

  def SetPanelsXY(self):
    for label in self.panels_.keys():
      # grppanel -> subpanel -> hpanel -> panel
      parent = self.panels_[label]['panel']
      for i in range(0, 4):
        (dx, dy) = parent.GetPositionTuple()
        self.panels_[label]['x'] += dx
        self.panels_[label]['y'] += dy
        parent = parent.GetParent()
      #print self.panels_[label]['x'], self.panels_[label]['y'], label

  def addNode(self, node, panel, parent):
    simg = wx.ArtProvider.GetBitmap(wx.ART_EXECUTABLE_FILE)
    subpanel = wx.Panel(panel, -1)
    hbox = wx.BoxSizer(wx.HORIZONTAL)
    btn = wx.Button(subpanel, wx.ID_ANY, node)
    btn.Bind(wx.EVT_BUTTON, self.onExec)
    itos = self.conf_.getInTopics(node)
    istr = reduce(lambda m,n:m+'\n  '+n, sorted(itos)) if len(itos) > 0 else ''
    otos = self.conf_.getOutTopics(node)
    ostr = reduce(lambda m,n:m+'\n  '+n, sorted(otos)) if len(otos) > 0 else ''
    btn.SetToolTip(wx.ToolTip("IN:\n  " + istr + "\nOUT:\n  " + ostr))
    hbox.Add(btn, flag=wx.ALL|wx.ALIGN_CENTER_VERTICAL, border=1)
    bmp = wx.BitmapButton(subpanel, -1, simg, name=node)
    bmp.SetToolTip(wx.ToolTip("setting"))
    bmp.Bind(wx.EVT_BUTTON, self.onSetting)
    hbox.Add(bmp, flag=wx.ALL|wx.ALIGN_CENTER_VERTICAL, border=1)
    subpanel.SetSizer(hbox)
    parent.Add(subpanel, flag=wx.ALL, border=2)

  def addButtons(self, panel, parent):
    subpanel = wx.Panel(panel, -1)
    hbox = wx.BoxSizer(wx.HORIZONTAL)
    btn = wx.Button(subpanel, wx.ID_ANY, "close")
    btn.Bind(wx.EVT_BUTTON, self.onClose)
    hbox.Add(btn, flag=wx.ALL|wx.ALIGN_CENTER_VERTICAL, border=1)
    subpanel.SetSizer(hbox)
    parent.Add(subpanel, flag=wx.ALL, border=2)

  def onExec(self, event):
    """Execute node."""
    btn = event.GetEventObject()
    #print self.conf_.getSameNodes(btn.GetLabelText())
    print "# rosrun or roslaunch %s" % (btn.GetLabelText())

  def onSetting(self, event):
    """Node setting."""
    bmp = event.GetEventObject()
    print "# param setting for %s" % (bmp.GetName())

  def onClose(self, event):
    self.Close()

class ComputingPanel(wx.Panel):
  """Computing Panel."""
  def __init__(self, parent, id):
    wx.Panel.__init__(self, parent, id)
    panel = self
    hbox = wx.BoxSizer(wx.HORIZONTAL)
    panel.SetSizer(hbox)

    rimg = wx.ArtProvider.GetBitmap(wx.ART_GO_FORWARD)
    conf = ComputingConfig('src/computing.xml')
    gnames = conf.getNames()
    for grp in [e2 for e1 in zip(gnames, [0]*len(gnames)) for e2 in e1][:-1]:
      if grp == 0:
        hbox.Add(wx.StaticBitmap(panel, -1, rimg), flag=wx.ALL|wx.ALIGN_CENTER_VERTICAL, border=2)
        continue
      subpanel = wx.Panel(panel, -1)
      sizer = wx.StaticBoxSizer(wx.StaticBox(subpanel, -1, grp), orient=wx.VERTICAL)
      for pkg in conf.getPackages(grp):
        btn = wx.Button(subpanel, -1, pkg)
        self.Bind(wx.EVT_BUTTON, self.onClick)
        sizer.Add(btn)
      subpanel.SetSizer(sizer)
      hbox.Add(subpanel, flag=wx.ALL, border=4)

  def onClick(self, event):
    btn = event.GetEventObject()
    #print btn.GetLabelText()
    dialog = PackageDialog(None, -1, btn.GetLabelText())
    dialog.ShowModal()
    dialog.Destroy()

class ComputingFrame(wx.Frame):
  """Computing Frame."""
  def __init__(self, parent, id, title):
    wx.Frame.__init__(self, parent, id, title);
    panel = ComputingPanel(self, -1)
    self.SetSize(panel.GetBestSize())
    self.Centre()
    self.Show(True)

class ComputingApp(wx.App):
  def OnInit(self):
    frame = ComputingFrame(None, -1, "computing tab test")
    self.SetTopWindow(frame)
    return True

if __name__ == "__main__":
  app = ComputingApp(0)
  app.MainLoop()
