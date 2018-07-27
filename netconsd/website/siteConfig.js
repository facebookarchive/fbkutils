/**
 * Copyright (c) 2017-present, Facebook, Inc.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */

/* List of projects/orgs using your project for the users page */
const users = [
];

const siteConfig = {
  title: 'netconsd' /* title for your website */,
  tagline: 'Extending the Linux netconsole',
  url: 'https://facebook.github.io' /* your website url */,
  baseUrl: '/netconsd/' /* base url for your project */,
  projectName: 'netconsd',
  organizationName: "facebookmicrosites",
  // For no header links in the top nav bar -> headerLinks: [],
  headerLinks: [
    {doc: 'overview', label: 'Docs'},
    {
      href: 'https://github.com/facebook/fbkutils/tree/master/netconsd',
      label: 'GitHub'
    },
    {blog: false, label: ''},
  ],
    
  users,
  /* path to images for header/footer */
  headerIcon: '',
  footerIcon: '',
  favicon: 'img/oss-color-logo.png',
  /* colors for website */
  colors: {
    primaryColor: '#d1a060',
    secondaryColor: '#42aaf4',
  },
  /* custom fonts for website */
  /*fonts: {
    myFont: [
      "Times New Roman",
      "Serif"
    ],
    myOtherFont: [
      "-apple-system",
      "system-ui"
    ]
  },*/
    
  // This copyright info is used in /core/Footer.js and blog rss/atom feeds.
  copyright:
    'Copyright © ' +
    new Date().getFullYear() +
    ' Facebook Inc. ',

  highlight: {
    // Highlight.js theme to use for syntax highlighting in code blocks
    theme: 'default',
  },

  // Add custom scripts here that would be placed in <script> tags
  scripts: ['https://buttons.github.io/buttons.js'],

  /* On page navigation for the current documentation page */
  onPageNav: 'separate',

  /* Open Graph and Twitter card images */
  ogImage: 'img/bpf_logo.png',
  twitterImage: 'img/bpf_logo.png',

  // You may provide arbitrary config keys to be used as needed by your
  // template. For example, if you need your repo's URL...
  repoUrl: 'https://github.com/facebookmicrosites/bpf',
};

module.exports = siteConfig;
